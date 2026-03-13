import os
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session
from app.config import settings
from google import genai
from google.genai import types
import edge_tts
from pydantic import BaseModel

router = APIRouter()

async def get_session():
    async with async_session() as session:
        yield session

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural" # Default edge-tts voice

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """Convert audio blob to text using Gemini Flash."""
    
    if not settings.gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API key not configured in settings.")
        
    client = genai.Client(api_key=settings.gemini_api_key)
    
    try:
        # Save temporary file for Gemini to read
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".webm"
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            
        # Gemini 2.5 Flash handles audio natively
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                'Please transcribe this audio accurately.',
                types.Part.from_bytes(
                    data=open(tmp_path, 'rb').read(),
                    mime_type='audio/webm' if suffix == '.webm' else 'audio/mpeg'
                )
            ]
        )
            
        return {"text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@router.post("/tts")
async def text_to_speech(
    req: TTSRequest,
    session: AsyncSession = Depends(get_session)
):
    """Convert text to speech stream using edge-tts."""
    try:
        # edge-tts is a free, high-quality Microsoft Edge TTS wrapper
        communicate = edge_tts.Communicate(req.text, req.voice)
        
        # We can stream the output
        async def iter_audio():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        return StreamingResponse(iter_audio(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
