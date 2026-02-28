
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


def get_chat_service(request: Request, session: AsyncSession = Depends(get_session)) -> ChatService:
    return ChatService(
        provider_registry=request.app.state.provider_registry,
        tool_registry=request.app.state.tool_registry,
        session=session,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, service: ChatService = Depends(get_chat_service)):
    conversation_id = req.conversation_id or ""
    response_text = await service.chat(
        conversation_id=conversation_id,
        user_message=req.message,
        model_string=req.model,
        system_prompt=req.system_prompt,
        temperature=req.temperature,
    )
    return ChatResponse(
        conversation_id=conversation_id,
        message=response_text,
    )


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type", "message")
            if msg_type != "message":
                continue

            content = data.get("content", "")
            model = data.get("model", "gemini/gemini-2.5-flash")
            temperature = data.get("temperature", 0.7)
            system_prompt = data.get("system_prompt")

            is_group = data.get("is_group", False)

            # Create a new session for this message exchange
            from app.db.engine import async_session
            async with async_session() as session:
                service = ChatService(
                    provider_registry=websocket.app.state.provider_registry,
                    tool_registry=websocket.app.state.tool_registry,
                    session=session,
                )

                try:
                    if is_group:
                        async for event in service.stream_group_chat(
                            conversation_id=conversation_id,
                            user_message=content,
                            temperature=temperature,
                        ):
                            await websocket.send_json(event)
                    else:
                        async for event in service.stream_chat(
                            conversation_id=conversation_id,
                            user_message=content,
                            model_string=model,
                            system_prompt=system_prompt,
                            temperature=temperature,
                        ):
                            await websocket.send_json(event)
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        pass
