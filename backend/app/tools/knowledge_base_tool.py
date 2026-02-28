import json
from app.tools.base import BaseTool
from app.services.document_service import DocumentService

class KnowledgeBaseTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_knowledge_base"

    @property
    def description(self) -> str:
        return (
            "Search the user's uploaded documents (Knowledge Base) for relevant information. "
            "Use this tool when the user asks questions about their uploaded files, data, or general reference documents."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant information in the knowledge base.",
                },
                "n_results": {
                    "type": "integer",
                    "description": "The number of text chunks to retrieve. Default is 3.",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, n_results: int = 3, **kwargs) -> str:
        # We can pass session=None since search_documents only uses ChromaDB
        doc_service = DocumentService(session=None)
        results = doc_service.search_documents(query, n_results=n_results)
        
        if not results:
            return "No relevant information found in the knowledge base."
            
        formatted = []
        for i, res in enumerate(results):
            filename = res.get('metadata', {}).get('filename', 'Unknown')
            content = res.get('content', '')
            formatted.append(f"--- Document: {filename} (Result {i+1}) ---\n{content}\n")
            
        return "\n".join(formatted)
