# tests/test_dataset_service.py
import os
import shutil
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from services.dataset_service import save_to_dataset

class MockMasks:
    def __init__(self, xyn):
        self.xyn = xyn

class MockResult:
    def __init__(self, xyn, filename="test.jpg"):
        self.masks = MockMasks(xyn)
        self.path = filename

@pytest.fixture
def mock_dataset_dir(tmp_path):
    """Temporary dataset directory for isolation."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_save_to_dataset_train_split(mock_dataset_dir):
    """Verify that images and labels are saved correctly in the 'train' folder."""
    # 1. Setup Mock Data (2 polygons)
    mock_xyn = [
        np.array([[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]]),
        np.array([[0.5, 0.5], [0.6, 0.5], [0.6, 0.6], [0.5, 0.6]])
    ]
    mock_result = MockResult(mock_xyn)
    dummy_img_bytes = b"fake-image-content"
    car_model = "Corolla"
    filename = "cam1_001.jpg"

    # 2. Call Service (Force train split)
    with patch("random.random", return_value=0.5): # 0.5 > 0.2 (default split), so stays in train
        res = save_to_dataset(dummy_img_bytes, mock_result, car_model, filename, test_split=0.2)

    # 3. Assertions
    assert res["is_test"] is False
    
    # Use .as_posix() or check for platform-independent paths
    assert "train/images" in Path(res["image_path"]).as_posix()
    assert Path(res["image_path"]).exists()
    assert Path(res["label_path"]).exists()

    # Verify Label formatting
    with open(res["label_path"], "r") as f:
        content = f.read().strip().split("\n")
        assert len(content) == 2
        # Verify first line starts with Class ID 0 and follows YOLO polygon format
        assert content[0].startswith("0 0.100000 0.100000 0.200000 0.100000")

def test_save_to_dataset_test_split(mock_dataset_dir):
    """Verify that images are correctly assigned to the 'test' split."""
    mock_xyn = [np.array([[0.0, 0.0], [1.0, 1.0]])]
    mock_result = MockResult(mock_xyn)
    
    with patch("random.random", return_value=0.1): # 0.1 < 0.2, so moves to test
        res = save_to_dataset(b"data", mock_result, "Civic", "test_img.png", test_split=0.2)
    
    assert res["is_test"] is True
    assert "test/images" in Path(res["image_path"]).as_posix()

def test_save_to_dataset_no_masks(mock_dataset_dir):
    """Ensure no label file content is created if no masks are detected (but file exists)."""
    mock_result = MockResult(None)
    mock_result.masks = None # Explicitly None
    
    res = save_to_dataset(b"data", mock_result, "Test", "no_mask.jpg")
    
    lbl_path = Path(res["label_path"])
    assert lbl_path.exists()
    with open(lbl_path, "r") as f:
        assert f.read() == "" # Empty label file
