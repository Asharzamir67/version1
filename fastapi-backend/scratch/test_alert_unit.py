from database import SessionLocal
from agents.tools import log_system_observation
from models.model_registry import SystemObservation

def test_critical_alert_logic():
    print("\n--- [UNIT TEST] Testing Critical Alert Logic ---")
    db = SessionLocal()
    try:
        severity = "CRITICAL"
        category = "HARDWARE"
        observation = "UNIT TEST: Total power failure on Node 5. Alerting systems should trigger."
        
        print(f"Calling log_system_observation with severity={severity}...")
        result = log_system_observation(db, severity, category, observation)
        print(f"Result: {result}")
        
        # Verify it exists in DB
        last_obs = db.query(SystemObservation).order_by(SystemObservation.created_at.desc()).first()
        if last_obs and last_obs.observation == observation:
            print("SUCCESS: Observation persisted in database.")
        else:
            print("FAILED: Observation not found or mismatch.")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    test_critical_alert_logic()
