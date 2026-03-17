import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.services.secret_manager import get_secret_manager
from app.tools.image_gen import ImageGenerationTool

async def test_image_gen():
    tool = ImageGenerationTool()
    prompt = "A beautiful futuristic city underwater with glowing bioluminescent plants and transparent domes."
    
    print(f"Testing image generation with prompt: {prompt}")
    try:
        result = await tool.execute(prompt=prompt, provider="google")
        print("\nResult:")
        print(result)
        
        if "Error" in result:
            print("\nFAIL: Tool returned an error.")
        else:
            print("\nSUCCESS: Tool returned a potential image link.")
            
    except Exception as e:
        print(f"\nCRASH: Exception during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_image_gen())
