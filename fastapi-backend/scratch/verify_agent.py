import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Base, engine
from agents.model_agent import get_current_model_status
from models.model_registry import SystemObservation

def test_agent_supervision():
    print("--- [TEST] Starting Agentic Supervisor Verification ---")
    db = SessionLocal()
    
    # 1. Test basic connectivity and tool usage
    print("\n[Step 1] Testing basic system status query...")
    response = get_current_model_status(db, "How many images are in the system?")
    print(f"Agent Response: {response['message']}")
    
    # 2. Test RCA Pattern Analysis
    print("\n[Step 2] Testing RCA Pattern Analysis...")
    response = get_current_model_status(db, "Perform an RCA on the quality data. Which camera is the most problematic?")
    print(f"Agent Response: {response['message']}")
    
    # 3. Test Persistent Memory (Observations)
    print("\n[Step 3] Testing observation logging...")
    response = get_current_model_status(db, "Log a critical observation that Camera 3 is showing lens flare issues.")
    print(f"Agent Response: {response['message']}")
    
    # Verify in DB
    obs = db.query(SystemObservation).filter(SystemObservation.severity == 'CRITICAL').first()
    if obs:
        print(f"SUCCESS: Found observation in DB: {obs.observation}")
    else:
        print("FAILURE: Observation not found in DB.")
        
    # 4. Test Historical Context
    print("\n[Step 4] Testing historical memory...")
    response = get_current_model_status(db, "What was the last critical observation you logged?")
    print(f"Agent Response: {response['message']}")
    
    db.close()
    print("\n--- [TEST] Verification Complete ---")

if __name__ == "__main__":
    test_agent_supervision()
