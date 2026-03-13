from app.config import settings
print(f"Gemini API Key set: {settings.gemini_api_key is not None}")
if settings.gemini_api_key:
    print(f"Gemini API Key starts with: {settings.gemini_api_key[:5]}...")
