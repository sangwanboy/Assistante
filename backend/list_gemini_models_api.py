
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ASSITANCE_GEMINI_API_KEY")

def list_models():
    if not api_key:
        print("No API key found")
        return

    client = genai.Client(api_key=api_key)
    print("Available Gemini models:")
    try:
        models = client.models.list()
        for m in models:
            print(f"- {m.name}: {m.display_name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
