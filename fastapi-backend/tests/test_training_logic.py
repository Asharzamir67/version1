# tests/test_training_logic.py
import pytest
from unittest.mock import MagicMock, patch
from services.training_service import run_training_pipeline
from models.model_registry import ModelVersion

@patch("services.training_service.YOLO")
@patch("services.training_service.generate_dataset_yaml")
@patch("services.training_service.SessionLocal")
@patch("services.training_service.reload_active_model")
def test_promotion_logic_success(mock_reload, mock_session, mock_yaml, mock_yolo, db_session):
    """
    Test that a new model is PROMOTED when its mAP is higher than the current champion.
    """
    # 1. Setup Mock DB
    mock_session.return_value = db_session
    # Prevent the close() call in the service from closing the test fixture session
    db_session.close = MagicMock()
    
    # Existing Champion (mAP: 0.80)
    champion = ModelVersion(car_model_name="Corolla", map_50_95=0.80, is_active=True, model_path="old.pt")
    db_session.add(champion)
    db_session.commit()
    
    # 2. Setup Mock YOLO results (Challenger: 0.85)
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    
    # Mock training results
    mock_train_result = MagicMock()
    mock_train_result.save_dir = "runs/test"
    mock_model_instance.train.return_value = mock_train_result
    
    # Mock validation results
    mock_val_result = MagicMock()
    mock_val_result.results_dict = {'metrics/mAP50-95(B)': 0.85}
    mock_model_instance.val.return_value = mock_val_result
    
    # 3. Run Pipeline
    run_training_pipeline("Corolla")
    
    # 4. Verify Promotion
    db_session.refresh(champion)
    new_active = db_session.query(ModelVersion).filter_by(is_active=True).first()
    assert new_active.map_50_95 == 0.85
    assert champion.is_active is False
    assert mock_reload.called

@patch("services.training_service.YOLO")
@patch("services.training_service.generate_dataset_yaml")
@patch("services.training_service.SessionLocal")
def test_promotion_logic_rejection(mock_session, mock_yaml, mock_yolo, db_session):
    """
    Test that a new model is REJECTED when its mAP is lower than the current champion.
    """
    mock_session.return_value = db_session
    db_session.close = MagicMock()
    
    # Existing Champion (mAP: 0.90)
    champion = ModelVersion(car_model_name="Civic", map_50_95=0.90, is_active=True, model_path="best.pt")
    db_session.add(champion)
    db_session.commit()
    
    # Challenger: 0.80
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    mock_train_result = MagicMock()
    mock_train_result.save_dir = "runs/test"
    mock_model_instance.train.return_value = mock_train_result
    
    mock_val_result = MagicMock()
    mock_val_result.results_dict = {'metrics/mAP50-95(B)': 0.80}
    mock_model_instance.val.return_value = mock_val_result
    
    # Run
    run_training_pipeline("Civic")
    
    # Verify Rejection
    db_session.refresh(champion)
    active = db_session.query(ModelVersion).filter_by(is_active=True).first()
    assert active.id == champion.id
    assert active.map_50_95 == 0.90
