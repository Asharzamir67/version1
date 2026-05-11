import sys
import os
# Add the current directory to path so we can import app modules
sys.path.append(os.getcwd())

from database import SessionLocal
from agents.model_agent import get_current_model_status

def test_agent_audit_flow():
    db = SessionLocal()
    try:
        print("\n--- Testing Agent Health Audit Flow ---")
        prompt = "How is the system quality doing today?"
        # The agent should call audit_system_quality() first according to SYSTEM_PROMPT
        result = get_current_model_status(db, prompt=prompt, thread_id="test_verification")
        print(f"Agent Response: {result['message']}")
        
        print("\n--- Testing 'Hi' Response (No Tools) ---")
        result_hi = get_current_model_status(db, prompt="Hi there!", thread_id="test_verification")
        print(f"Agent Response: {result_hi['message']}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_agent_audit_flow()
