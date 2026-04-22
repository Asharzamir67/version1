# tests/test_evaluator_service.py
import os
import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from services.evaluator_service import generate_dataset_yaml, evaluate_model_performance

@pytest.fixture
def temp_dataset_dir(tmp_path):
    """Temporary dataset directory Setup."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    # Create mock dataset folders
    (tmp_path / "dataset" / "Corolla" / "test" / "images").mkdir(parents=True)
    with open(tmp_path / "dataset" / "Corolla" / "test" / "images" / "test.jpg", "w") as f:
        f.write("fake")
        
    yield tmp_path
    os.chdir(original_cwd)

def test_generate_dataset_yaml(temp_dataset_dir):
    """Verify that the generated YOLO YAML file has the correct structure."""
    car_models = ["Corolla", "Civic"]
    yaml_path = generate_dataset_yaml(car_models)
    
    assert os.path.exists(yaml_path)
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
        assert config["names"] == {0: "sealant"}
        assert len(config["test"]) == 2
        assert "Corolla/test/images" in config["test"]

@patch("services.evaluator_service.YOLO")
@patch("services.evaluator_service.get_active_model_info_from_db")
def test_evaluate_model_performance_success(mock_info, mock_yolo, temp_dataset_dir):
    """Verify model valuation result processing (mAP, Precision, Recall)."""
    # 1. Setup Mocks
    mock_info.return_value = ("best.pt", "Corolla")
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    
    # Mock results_dict returned by model.val()
    mock_results = MagicMock()
    mock_results.results_dict = {
        'metrics/mAP50(B)': 0.90,
        'metrics/mAP50-95(B)': 0.85,
        'metrics/precision(B)': 0.88,
        'metrics/recall(B)': 0.82
    }
    mock_model_instance.val.return_value = mock_results

    # 2. Call service
    response = evaluate_model_performance("Corolla")

    # 3. Assertions
    assert response["success"] is True
    assert "Aggregate mAP@50-95: 0.8500" in response["report"]
    assert response["suggest_retrain"] is False # 0.85 > 0.70 threshold

@patch("services.evaluator_service.YOLO")
@patch("services.evaluator_service.get_active_model_info_from_db")
def test_evaluate_model_performance_needs_retrain(mock_info, mock_yolo, temp_dataset_dir):
    """Verify that retrain recommendation is triggered on low mAP."""
    mock_info.return_value = ("best.pt", "Corolla")
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    
    mock_results = MagicMock()
    mock_results.results_dict = {'metrics/mAP50-95(B)': 0.40} # Very low accuracy
    mock_model_instance.val.return_value = mock_results

    response = evaluate_model_performance("Corolla")

    assert response["success"] is True
    assert response["suggest_retrain"] is True
    assert "Conclusion: I recommend STARTING RETRAINING" in response["report"]
