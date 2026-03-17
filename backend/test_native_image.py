import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.services.secret_manager import get_secret_manager
from google import genai
from google.genai import types

async def test_native_gen():
    sm = get_secret_manager()
    api_key = sm.get_api_key("gemini")
    if not api_key:
        print("Error: Gemini API key not found.")
        return

    client = genai.Client(api_key=api_key)
    prompt = "Generate a realistic image of a neon sign that says 'ANTIGRAVITY'. Return the image bytes inline."
    
    # Try multiple models with the 'models/' prefix
    models_to_try = [
        'models/gemini-2.0-flash',
        'models/gemini-2.0-flash-001',
        'models/gemini-2.5-flash',
        'models/gemini-3.1-pro-preview', # User mentioned 3.1
    ]
    
    for model_id in models_to_try:
        print(f"\nAttempting native generation with {model_id}...")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # Some models might need specific flags for native generation
                    # but usually it's just multimodal
                )
            )
            print(f"Response received from {model_id}!")
            
            has_image = False
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                print(f"Found inline_data! Mime type: {part.inline_data.mime_type}")
                                has_image = True
                            if part.file_data:
                                print(f"Found file_data! URI: {part.file_data.file_uri}")
                                has_image = True
            
            if not has_image:
                print("No native image found in response.")
                print("Text response head:", response.text[:200] if response.text else "None")
                
        except Exception as e:
            print(f"Error with {model_id}: {e}")

if __name__ == "__main__":
    asyncio.run(test_native_gen())
