# tests/test_inference_service.py
import pytest
from unittest.mock import MagicMock, patch
from services.inference import ModelPool, reload_active_model

@pytest.fixture
def mock_yolo():
    """Mocks the YOLO instantiation to prevent GPU/Memory hit."""
    with patch("services.inference.YOLO") as mock:
        yield mock

@pytest.fixture
def mock_db_info():
    """Mocks the database lookup for metadata."""
    with patch("services.inference.get_active_model_info_from_db") as mock:
        mock.return_value = ("best.pt", "Corolla")
        yield mock

def test_model_pool_lazy_initialization(mock_db_info, mock_yolo):
    """Verify that ModelPool does NOT load models until get_model is called."""
    pool = ModelPool(size=2)
    
    # 1. Initially, no YOLO instances should be created
    assert pool.initialized is False
    assert mock_yolo.call_count == 0
    
    # 2. Triggering get_model should load models
    with pool.get_model() as model:
        assert pool.initialized is True
        assert mock_yolo.call_count == 2
        assert model is not None
        
    # 3. Subsequent calls should NOT reload
    with pool.get_model() as model:
        assert mock_yolo.call_count == 2 # Still 2

def test_model_pool_reload_logic(mock_db_info, mock_yolo):
    """Verify that reload() resets the pool state but stays lazy."""
    pool = ModelPool(size=1)
    
    # Init first
    with pool.get_model():
        pass
    assert mock_yolo.call_count == 1
    
    # Trigger Reload (scheduled)
    mock_db_info.return_value = ("new_weights.pt", "Civic")
    pool.reload()
    
    assert pool.initialized is False # Reset
    assert pool.current_path == "new_weights.pt"
    
    # Real load on next access
    with pool.get_model():
        pass
    assert mock_yolo.call_count == 2 # 1 (original) + 1 (reloaded)

@patch("services.inference.bytes_to_image")
@patch("services.inference.model_pool")
def test_run_threaded_inference(mock_pool, mock_bytes):
    """Verify that threaded inference correctly uses pool context."""
    # Ensure bytes_to_image doesn't fail and has a valid shape
    mock_img = MagicMock()
    mock_img.shape = (480, 640, 3)
    mock_bytes.return_value = mock_img
    
    # 1. Setup Mock Pool
    mock_model_instance = MagicMock()
    
    # Mock context manager
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_model_instance
    mock_pool.get_model.return_value = mock_cm
    
    # Dummy result
    mock_res = MagicMock()
    mock_model_instance.predict.return_value = [mock_res]
    
    # 2. Call Service
    dummy_bytes = [b"a", b"b"]
    
    from services.inference import run_threaded_inference
    results = run_threaded_inference(dummy_bytes)
    
    # 3. Assertions
    assert len(results) == 2
    assert mock_pool.get_model.call_count == 2
    assert results[0] == mock_res
