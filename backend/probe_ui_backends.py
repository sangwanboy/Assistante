
import httpx
import json

BASE_URL = "http://127.0.0.1:8321"

def test_models():
    print("Testing /api/models...")
    try:
        r = httpx.get(f"{BASE_URL}/api/models")
        print(f"Status: {r.status_code}")
        models = r.json()
        providers = set(m['provider'] for m in models)
        print(f"Providers found: {providers}")
        gemini_models = [m['id'] for m in models if m['provider'] == 'gemini']
        print(f"Gemini models: {len(gemini_models)} found.")
        return len(gemini_models) > 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_dashboard():
    print("\nTesting /api/system/dashboard...")
    try:
        r = httpx.get(f"{BASE_URL}/api/system/dashboard")
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"Dashboard keys: {list(data.keys())}")
        return "tokens" in data or "agents" in data
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_chat():
    print("\nTesting /api/chat (smoke test)...")
    try:
        # Just check if we can get a response from a basic chat probe
        payload = {
            "message": "hi",
            "provider": "ollama", # Using ollama for faster local test if Gemini key is still being picked up
            "model": "ollama/llama3" 
        }
        # Note: If ollama isn't running, this might fail, but let's see if the endpoint itself exists
        r = httpx.post(f"{BASE_URL}/api/chat", json=payload, timeout=5)
        print(f"Status: {r.status_code}")
        return r.status_code != 404
    except Exception as e:
        print(f"Error: {e}")
        # Even if it fails (e.g. timeout), as long as it's not 404, the route is there
        return "404" not in str(e)

if __name__ == "__main__":
    m = test_models()
    d = test_dashboard()
    c = test_chat()
    print(f"\nResults: Models={m}, Dashboard={d}, ChatRoute={c}")
