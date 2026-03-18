import litellm

try:
    response = litellm.completion(
        model="gemini/gemini-2.5-flash", 
        messages=[{"role": "user", "content": "hi"}], 
        api_key="AIzaSyBoXubRIVAWm5mKii3mktM2D9GUBVMA-dk"
    )
    print("SUCCESS")
    print(response.choices[0].message.content)
except Exception as e:
    print("FAILED")
    print(e)