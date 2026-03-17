
import os
from google import genai
from app.config import settings

def list_gemini_models():
    api_key = settings.gemini_api_key
    if not api_key:
        print("No Gemini API key found.")
        return
        
    client = genai.Client(api_key=api_key)
    print("Listing available Gemini models:")
    try:
        for model in client.models.list():
            print(f"- {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
