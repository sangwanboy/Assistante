from google import genai
import os
import dotenv

# Load .env to get the API key
dotenv.load_dotenv('backend/.env')
api_key = os.getenv('ASSITANCE_GEMINI_API_KEY')

if not api_key:
    print("No Gemini API key found in backend/.env")
    exit(1)

client = genai.Client(api_key=api_key)

try:
    print("Fetching available models...")
    for model in client.models.list():
        print(f"ID: {model.name}")
except Exception as e:
    print(f"Error: {e}")
