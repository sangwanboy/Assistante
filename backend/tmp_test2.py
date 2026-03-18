import asyncio
import litellm
import os

litellm.api_key='AIzaSyBTzCF7Uh50d5IyvyZmg_pVdOvZngnsM2U'

async def test():
    stream = await litellm.acompletion(
        model='gemini/gemini-3-pro-preview', 
        messages=[{'role': 'user', 'content': 'what is 2+2? tell me via tool'}], 
        tools=[{'type': 'function', 'function': {'name': 'tell_sum', 'description': 'tell the sum', 'parameters': {'type': 'object', 'properties': {'sum': {'type': 'integer'}}}}}] ,
        stream=False
    )
    print(stream.choices[0])

asyncio.run(test())