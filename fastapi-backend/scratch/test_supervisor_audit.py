import os
import sys
from datetime import datetime, timedelta

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.inference_result import InferenceResult
from agents.model_agent import get_current_model_status

def run_test():
    db = SessionLocal()
    try:
        print("--- [TEST] Injecting Simulated Failure Data ---")
        # Create 10 OK records from yesterday
        yesterday = datetime.now() - timedelta(days=1)
        for i in range(10):
            db.add(InferenceResult(
                car_model="TestCorolla",
                image1_status="ok", image2_status="ok", image3_status="ok", image4_status="ok",
                input_time=yesterday
            ))
        
        # Create 10 NG records from the last 15 minutes (Camera 1 failure)
        now = datetime.now()
        for i in range(10):
            db.add(InferenceResult(
                car_model="TestCorolla",
                image1_status="ng", image2_status="ok", image3_status="ok", image4_status="ok",
                input_time=now - timedelta(minutes=i)
            ))
        
        db.commit()
        print("✅ Injected 10 historical OKs and 10 recent NGs.")

        print("\n--- [TEST] Triggering AI Supervisor Audit ---")
        prompt = (
            "Perform a system quality audit. "
            "Use your tools to find if there's a spike in NG results. "
            "If found, identify which camera is failing and check the error logs for clues. "
            "Finally, log a CRITICAL observation if you find a pattern."
        )
        
        result = get_current_model_status(db, prompt=prompt, thread_id="test_audit_1")
        
        print("\n--- [AGENT RESPONSE] ---")
        print(result["message"])
        print("------------------------")

        # Verify observation was logged
        from models.model_registry import SystemObservation
        obs = db.query(SystemObservation).order_by(SystemObservation.created_at.desc()).first()
        if obs:
            print(f"\n✅ RECENT LOGGED OBSERVATION: [{obs.severity}] {obs.observation}")
        else:
            print("\n❌ No observation was logged by the agent.")

    except Exception as e:
        print(f"❌ Test Failed: {str(e)}")
    finally:
        # Cleanup test data (optional, but good for hygiene)
        # db.query(InferenceResult).filter(InferenceResult.car_model == "TestCorolla").delete()
        # db.commit()
        db.close()

if __name__ == "__main__":
    run_test()
