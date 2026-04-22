import sys
import os

# Set PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing imports...")
    from agents.model_agent import agent_manager, get_current_model_status
    from database import SessionLocal
    print("Imports successful!")

    print("Checking AgentManager app...")
    if agent_manager.app:
        print("AgentManager graph compiled successfully!")
    
    print("Test passed!")
except Exception as e:
    print(f"Test failed with error: {str(e)}")
    sys.exit(1)
