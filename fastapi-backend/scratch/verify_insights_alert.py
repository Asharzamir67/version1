import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api_fetch():
    print("\n[TEST] Testing /api/system-observations fetch...")
    try:
        response = requests.get(f"{BASE_URL}/api/system-observations")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Fetched {data['total']} observations.")
            if data['observations']:
                print(f"Latest: {data['observations'][0]['observation']}")
        else:
            print(f"FAILED: Status {response.status_code}")
    except Exception as e:
        print(f"ERROR: {str(e)}")

def test_critical_alert_flow():
    print("\n[TEST] Testing CRITICAL alert flow via Agent...")
    from agents.model_agent import get_current_model_status
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        # Prompt the agent to log a critical hardware error
        prompt = "LOG CRITICAL OBSERVATION: 'Emergency: Camera 4 has suffered a catastrophic failure. Immediate replacement required.'"
        print("Dispatching critical prompt to agent...")
        get_current_model_status(db, prompt=prompt, thread_id="alert_test")
        print("\nCHECK CONSOLE ABOVE: Did you see the [!!! CRITICAL SYSTEM ALERT !!!] block?")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure the server is running or we can test the DB directly
    print("--- Starting Insights & Alert Verification ---")
    test_api_fetch()
    test_critical_alert_flow()
    print("\n--- Verification Complete ---")
