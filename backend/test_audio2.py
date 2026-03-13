import asyncio
import edge_tts
from google import genai
from app.config import settings

async def test_tts():
    try:
        communicate = edge_tts.Communicate("Hello", "en-US-GuyNeural")
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                print("Got audio chunk!", len(chunk["data"]))
                break
    except Exception as e:
        print("TTS Error:", e)

async def test_stt():
    try:
        if not settings.gemini_api_key:
            print("No gemini api key")
            return
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=['test']
        )
        print("STT Gemini Response:", response.text)
    except Exception as e:
        print("STT Error:", e)

async def main():
    await test_tts()
    await test_stt()

asyncio.run(main())
