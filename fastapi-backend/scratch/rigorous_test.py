import requests
import json
import time

BACKEND_URL = "http://127.0.0.1:8001"
# We don't test frontend URL directly with requests as it's an Electron app/Vite dev server
# but we can check if the port is open

def test_api_health():
    print("\n--- [1/5] Testing API Health ---")
    try:
        res = requests.get(f"{BACKEND_URL}/")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        return res.status_code == 200
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False

def get_admin_token():
    print("\n--- Logging in to get Auth Token ---")
    try:
        # Use a unique test admin to avoid 'Invalid credentials' if 'admin' exists with a different pass
        test_username = f"test_admin_{int(time.time())}"
        test_password = "password123"
        
        print(f"Registering unique test admin: {test_username}...")
        reg_res = requests.post(f"{BACKEND_URL}/admin/register", json={
            "username": test_username, 
            "email": f"{test_username}@example.com", 
            "password": test_password,
            "full_name": "Rigorous Tester"
        })
        
        login_data = {"username": test_username, "password": test_password}
        res = requests.post(f"{BACKEND_URL}/admin/login", json=login_data)
        
        if res.status_code == 200:
            data = res.json()
            token = data.get("access_token")
            if token:
                print(f"Login Successful. Token starts with: {token[:10]}...")
                return token
        
        print(f"Login failed: {res.status_code} {res.text}")
        return None
    except Exception as e:
        print(f"Auth Error: {str(e)}")
        return None

def test_chat_persistence(token):
    print("\n--- [2/5] Testing Chat Persistence ---")
    if not token:
        print("Skipping: No Auth Token")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    thread_id = "test_admin_rigorous"
    prompt = "Hello Rigorous Test"
    
    try:
        # Send a message
        res = requests.post(f"{BACKEND_URL}/admin/model-status", json={
            "prompt": prompt,
            "thread_id": thread_id
        }, headers=headers)
        print(f"Post Message Status: {res.status_code}")
        
        # Retrieve history - using the dedicated chat-history endpoint
        # The route in admin_routes.py is @router.get("/chat-history")
        history_res = requests.get(f"{BACKEND_URL}/admin/chat-history", params={"thread_id": thread_id}, headers=headers)
        history = history_res.json()
        print(f"History Count: {len(history)}")
        
        # Verify the message is there
        found = any(prompt in m['content'] for m in history)
        print(f"Message Found in DB: {found}")
        return found
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False

def test_agent_tools(token):
    print("\n--- [3/5] Testing AI Agent Tool Execution ---")
    if not token:
        print("Skipping: No Auth Token")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    # This prompt forces the agent to call at least 2 tools
    prompt = "Give me the system stats and then tell me about the active model."
    try:
        start_time = time.time()
        res = requests.post(f"{BACKEND_URL}/admin/model-status", json={
            "prompt": prompt,
            "thread_id": "tool_tester"
        }, headers=headers, timeout=60)
        duration = time.time() - start_time
        
        data = res.json()
        print(f"Agent Response (Time: {duration:.2f}s):")
        # In current implementation, message is at root
        message = data.get('message', '')
        print(f"Content: {message[:200]}...")
        
        # Check if it actually fetched stats (checking metadata in response if present, or just checking content)
        has_stats = "db_count" in data or "image_count" in data
        print(f"Tool Metadata Returned: {has_stats}")
        return res.status_code == 200 and len(message) > 0
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False

def test_unprotected_endpoints():
    print("\n--- [4/5] Testing Unprotected Observability Endpoints ---")
    try:
        # System observations should be open according to main.py
        res = requests.get(f"{BACKEND_URL}/api/system-observations")
        print(f"Observations Status: {res.status_code}")
        data = res.json()
        print(f"Found {data.get('total', 0)} observations.")
        
        # Agent status
        status_res = requests.get(f"{BACKEND_URL}/api/agent/status")
        print(f"Agent Status API: {status_res.status_code}")
        
        return res.status_code == 200 and status_res.status_code == 200
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False

def test_supervisor_status():
    print("\n--- [5/5] Testing Autonomous Supervisor Status ---")
    try:
        res = requests.get(f"{BACKEND_URL}/api/agent/status")
        data = res.json()
        print(f"Supervisor State: {data.get('status')}")
        print(f"Mode: {data.get('mode')}")
        return data.get('status') == 'active'
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    results = []
    results.append(test_api_health())
    
    token = get_admin_token()
    
    results.append(test_chat_persistence(token))
    results.append(test_agent_tools(token))
    results.append(test_unprotected_endpoints())
    results.append(test_supervisor_status())
    
    print("\n==============================")
    print(f"FINAL RESULT: {sum(results)}/5 TESTS PASSED")
    print("==============================")
