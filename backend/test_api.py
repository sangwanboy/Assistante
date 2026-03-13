import asyncio
from app.db.engine import async_session
from app.services.document_service import DocumentService

async def run():
    async with async_session() as s:
        svc = DocumentService(s)
        try:
            docs = await svc.list_documents()
            print(f"Docs: {docs}")
        except Exception:
            import traceback
            traceback.print_exc()

asyncio.run(run())
