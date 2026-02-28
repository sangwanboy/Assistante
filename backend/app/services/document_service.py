import os
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile
import chromadb
from chromadb.utils import embedding_functions

from app.models.document import Document
import PyPDF2

CHROMA_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "chroma")

class DocumentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        # Initialize ChromaDB client (local persistent)
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        # Use sentence-transformers default embedding
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn
        )

    async def list_documents(self) -> List[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_document(self, doc_id: str) -> Optional[Document]:
        stmt = select(Document).where(Document.id == doc_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_document(self, doc_id: str) -> bool:
        doc = await self.get_document(doc_id)
        if not doc:
            return False
        
        # Remove from vector DB
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            print(f"Error deleting from ChromaDB: {e}")

        await self.session.delete(doc)
        await self.session.commit()
        return True

    def _extract_text(self, file_path: str, content_type: str) -> str:
        text = ""
        if "pdf" in content_type.lower() or file_path.endswith(".pdf"):
            try:
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            except Exception as e:
                print(f"PDF extraction error: {e}")
        else:
            # Assume text
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"Text extraction error: {e}")
        return text

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    async def upload_document(self, file: UploadFile, upload_dir: str) -> Document:
        content = await file.read()
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if already exists based on hash to prevent duplicates
        stmt = select(Document).where(Document.content_hash == content_hash)
        result = await self.session.execute(stmt)
        existing_doc = result.scalar_one_or_none()
        
        if existing_doc:
            return existing_doc

        doc_id = f"doc_{content_hash[:12]}"
        
        # Save file to disk
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(content)

        # Create DB record
        doc = Document(
            id=doc_id,
            filename=file.filename,
            file_type=file.content_type or "application/octet-stream",
            size=len(content),
            content_hash=content_hash,
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        
        # Extract text and ingest to Vector DB
        text = self._extract_text(file_path, str(file.content_type))
        if text.strip():
            chunks = self._chunk_text(text)
            if chunks:
                ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
                metadatas = [{"doc_id": doc_id, "filename": file.filename, "chunk_index": i} for i in range(len(chunks))]
                
                # Add to ChromaDB
                self.collection.add(
                    documents=chunks,
                    metadatas=metadatas,
                    ids=ids
                )
        
        return doc

    def search_documents(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search the vector database for relevant chunks."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            structured_results = []
            if results["documents"] and len(results["documents"]) > 0:
                docs = results["documents"][0]
                metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
                
                for i in range(len(docs)):
                    structured_results.append({
                        "content": docs[i],
                        "metadata": metadatas[i]
                    })
            return structured_results
        except Exception as e:
            print(f"Search error: {e}")
            return []
