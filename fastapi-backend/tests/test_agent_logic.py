# tests/test_agent_logic.py
import pytest
from unittest.mock import MagicMock, patch
from agents.model_agent import get_current_model_status
from models.inference_result import InferenceResult
from models.model_registry import ModelVersion

@pytest.fixture
def mock_agent_app():
    """Mock the LangGraph app to avoid real LLM calls."""
    with patch("agents.model_agent.StateGraph") as mock_graph:
        mock_app = MagicMock()
        mock_graph.return_value.compile.return_value = mock_app
        
        # Mock final output
        mock_msg = MagicMock()
        mock_msg.content = "Analysis: Retraining is recommended for Corolla."
        mock_app.invoke.return_value = {"messages": [mock_msg]}
        
        yield mock_app

@patch("agents.model_agent.get_active_model_info_from_db")
def test_agent_status_response(mock_info, mock_agent_app, db_session):
    """Test the agent entry point without calling real LLM."""
    # 1. Setup Data
    mock_info.return_value = ("best.pt", "Corolla")
    
    # Add dummy inference result
    res = InferenceResult(car_model="Corolla", image1_status="ok", is_test_set=False)
    db_session.add(res)
    db_session.commit()
    
    # 2. Invoke Agent logic
    prompt = "Give me a summary of Corolla performance."
    result = get_current_model_status(db_session, prompt=prompt)
    
    # 3. Assertions
    assert "Retraining is recommended" in result["message"]
    assert result["model_name"] == "Corolla"
    assert result["db_count"] >= 1

@patch("agents.model_agent.ChatGroq")
def test_agent_tool_selection_call(mock_chat, db_session):
    """(Optional) Deep check that LLM is initialized with tools."""
    # We don't want to run the full graph here, just check binding
    prompt = "How many images?"
    get_current_model_status(db_session, prompt=prompt)
    
    # Verify that ChatGroq was initialized with the expected model
    mock_chat.assert_called_with(model="llama-3.3-70b-versatile", temperature=0.1)
