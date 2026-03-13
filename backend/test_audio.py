import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        # test TTS
        print("Testing TTS...")
        try:
            res = await client.post("http://127.0.0.1:8321/api/audio/tts", json={"text": "Hello world"})
            print("TTS Status:", res.status_code)
            if res.status_code != 200:
                print("TTS Error:", res.text)
        except Exception as e:
            print("TTS Request Exception:", str(e))
            
        # create dummy webm
        with open("dummy.webm", "wb") as f:
            f.write(b"empty audio")
            
        print("Testing Transcribe...")
        try:
            with open("dummy.webm", "rb") as f:
                res = await client.post("http://127.0.0.1:8321/api/audio/transcribe", files={"file": ("dummy.webm", f, "audio/webm")})
                print("Transcribe Status:", res.status_code)
                if res.status_code != 200:
                    print("Transcribe Error:", res.text)
        except Exception as e:
            print("Transcribe Request Exception:", str(e))

asyncio.run(test())
