# tests/conftest.py
import os
os.environ["YOLO_DEVICE"] = "cpu"
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import os

# Use a local SQLite file for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.sqlite"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    # Import models here to ensure they're registered with Base
    from models.inference_result import InferenceResult
    from models.model_registry import ModelVersion
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup after all tests
    if os.path.exists("./test_db.sqlite"):
        os.remove("./test_db.sqlite")

@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    # Disable expire_on_commit so objects stay readable after commit in tests
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
