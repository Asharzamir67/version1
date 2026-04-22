# tests/test_model_registry.py
from models.model_registry import ModelVersion

def test_create_model_version(db_session):
    """Test creating a new model version and saving metrics."""
    new_model = ModelVersion(
        car_model_name="Corolla",
        version_number=1,
        model_path="runs/test/weights/best.pt",
        map_50_95=0.82,
        is_active=True
    )
    db_session.add(new_model)
    db_session.commit()
    
    saved = db_session.query(ModelVersion).filter_by(car_model_name="Corolla").first()
    assert saved.version_number == 1
    assert saved.map_50_95 == 0.82
    assert saved.is_active is True

def test_active_model_logic(db_session):
    """Test that multiple models can exist but we can filter for the active one."""
    v1 = ModelVersion(car_model_name="Civic", version_number=1, map_50_95=0.75, is_active=False)
    v2 = ModelVersion(car_model_name="Civic", version_number=2, map_50_95=0.85, is_active=True)
    
    db_session.add_all([v1, v2])
    db_session.commit()
    
    active = db_session.query(ModelVersion).filter_by(car_model_name="Civic", is_active=True).first()
    assert active.version_number == 2
    assert active.map_50_95 == 0.85
