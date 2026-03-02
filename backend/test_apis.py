"""Full API test suite for Assitance app."""
import urllib.request
import json
import sys

BASE = "http://localhost:8321/api"
results = []

def test(name, method, path, body=None, expect_status=200):
    url = f"{BASE}{path}"
    try:
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req)
        status = resp.status
        ok = status == expect_status
        resp_body = resp.read().decode()
        result = json.loads(resp_body) if resp_body else None
        results.append((name, "PASS" if ok else f"FAIL ({status})", ""))
        return result
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        if e.code == expect_status:
            results.append((name, "PASS", ""))
        else:
            results.append((name, f"FAIL ({e.code})", body_text[:100]))
        return None
    except Exception as e:
        results.append((name, f"ERROR", str(e)[:100]))
        return None

# ─── Core ───
test("GET /health", "GET", "/../health")
test("GET /models", "GET", "/models")
test("GET /tools", "GET", "/tools")
test("GET /settings", "GET", "/settings")

# ─── Agents ───
test("GET /agents", "GET", "/agents")
agent = test("POST /agents", "POST", "/agents", {
    "name": "TestBot", "description": "Test agent",
    "provider": "gemini", "model": "gemini/gemini-2.5-flash",
    "system_prompt": "You are a test bot."
})
agent_id = agent["id"] if agent else None
if agent_id:
    test("GET /agents/{id}", "GET", f"/agents/{agent_id}")
    test("PUT /agents/{id}", "PUT", f"/agents/{agent_id}", {
        "name": "TestBot Updated", "description": "Updated",
        "provider": "gemini", "model": "gemini/gemini-2.5-flash",
        "system_prompt": "Updated prompt."
    })

# ─── Conversations ───
test("GET /conversations", "GET", "/conversations")
conv = test("POST /conversations", "POST", "/conversations", {"model": "gemini-2.5-flash"})
conv_id = conv["id"] if conv else None
if conv_id:
    test("GET /conversations/{id}", "GET", f"/conversations/{conv_id}")
    test("GET /conversations/{id}/messages", "GET", f"/conversations/{conv_id}/messages")

# ─── Channels ───
test("GET /channels", "GET", "/channels")
channel = test("POST /channels", "POST", "/channels", {
    "name": "TestChannel", "description": "Test group"
})
channel_id = channel["id"] if channel else None
if channel_id:
    test("GET /channels/{id}", "GET", f"/channels/{channel_id}")

# ─── Workflows ───
test("GET /workflows", "GET", "/workflows")
wf = test("POST /workflows", "POST", "/workflows", {
    "name": "TestWorkflow", "description": "Test"
})
wf_id = wf["id"] if wf else None
if wf_id:
    test("GET /workflows/{id}", "GET", f"/workflows/{wf_id}")
    test("GET /workflows?agent_id filter", "GET", "/workflows?agent_id=nonexistent")

# ─── Knowledge ───
test("GET /knowledge", "GET", "/knowledge")

# ─── Custom Tools ───
test("GET /custom-tools", "GET", "/custom-tools")

# ─── Skills ───
test("GET /skills", "GET", "/skills")

# ─── Cleanup ───
if agent_id:
    test("DELETE /agents/{id}", "DELETE", f"/agents/{agent_id}")
if conv_id:
    test("DELETE /conversations/{id}", "DELETE", f"/conversations/{conv_id}")
if channel_id:
    test("DELETE /channels/{id}", "DELETE", f"/channels/{channel_id}")
if wf_id:
    test("DELETE /workflows/{id}", "DELETE", f"/workflows/{wf_id}")

# ─── Print Results ───
print("\n" + "="*60)
print("  API TEST RESULTS")
print("="*60)
passed = sum(1 for _, s, _ in results if s == "PASS")
total = len(results)
for name, status, detail in results:
    icon = "+" if status == "PASS" else "X"
    line = f"  {icon} {status:12s} {name}"
    if detail:
        line += f" -- {detail}"
    print(line)
print(f"\n  {passed}/{total} PASSED")
print("="*60)
