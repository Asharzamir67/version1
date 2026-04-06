# tests/test_integration_api.py
import io
import json
import zipfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from main import app
from utils.dependencies import get_current_user
from database import Base

# --- Mocking Dependencies ---
async def mock_get_current_user():
    return {"id": 1, "username": "testuser"}

@pytest.fixture(autouse=True)
def override_dependencies(db_session):
    """Force FastAPI to use the same SQLite session as the test."""
    from utils.dependencies import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides = {}

client = TestClient(app)

@pytest.fixture
def mock_yolo_result():
    """Create a mock YOLO result that satisfies the processing pipeline."""
    result = MagicMock()
    result.filename = "test.jpg"
    result.plot.return_value = (np.zeros((640, 640, 3), dtype=np.uint8)) # Black image
    result.masks.xyn = [np.array([[0.1, 0.1], [0.2, 0.2]])]
    return result

import numpy as np

def test_process_images_integration(db_session):
    """
    Test the full image processing pipeline:
    Upload -> Mock Inference -> ZIP Packaging -> DB Entry -> Dataset Saving
    """
    # 1. Setup Mocks
    mock_results = [MagicMock() for _ in range(4)]
    for i, r in enumerate(mock_results):
        r.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        r.masks.xyn = [np.array([[0.1, 0.1], [0.5, 0.5]])]
        r.filename = f"img_{i}.jpg"

    with patch("routes.image_routes.run_threaded_inference", return_value=mock_results), \
         patch("routes.image_routes.detect_defects", return_value="ok"), \
         patch("routes.image_routes.save_to_dataset") as mock_save:
        
        # Mock the dataset saving return value
        mock_save.return_value = {"is_test": False, "image_path": "path/to/img", "label_path": "path/to/lbl"}

        # 2. Prepare payload (4 dummy images)
        files = [
            ("images", (f"test_{i}.jpg", io.BytesIO(b"fake_data"), "image/jpeg"))
            for i in range(4)
        ]
        data = {
            "model": "Corolla",
            "metadata": "TestBatch_001"
        }

        # 3. Execute Request
        response = client.post("/images/process", files=files, data=data)

        # 4. Verifications
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

        # Verify ZIP content
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content) as z:
            file_list = z.namelist()
            assert "results.json" in file_list
            assert any(f.startswith("processed/test_") for f in file_list)
            
            # Check results.json content
            res_json = json.loads(z.read("results.json"))
            assert res_json["model"] == "Corolla"
            assert len(res_json["summary"]) == 4
            assert res_json["summary"][0]["defect"] == "ok"

        # Verify DB Entry
        from models.inference_result import InferenceResult
        db_record = db_session.query(InferenceResult).filter_by(car_model="Corolla").first()
        assert db_record is not None
        assert db_record.image1_status == "ok"
        assert db_record.is_test_set is False

def test_process_images_validation_error():
    """Verify that the API rejects requests with incorrect number of images."""
    files = [("images", ("test.jpg", b"data", "image/jpeg"))] # Only 1 image
    response = client.post("/images/process", files=files, data={"model": "A", "metadata": "B"})
    assert response.status_code == 400
    assert "Exactly 4 images required" in response.json()["detail"]
