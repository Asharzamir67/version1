from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base

class InferenceResult(Base):
    __tablename__ = "inference_results"

    id = Column(Integer, primary_key=True, index=True)
    input_time = Column(DateTime(timezone=True), server_default=func.now())
    car_model = Column(String, index=True)
    image1_status = Column(String)  # "ok" or "ng"
    image2_status = Column(String)  # "ok" or "ng"
    image3_status = Column(String)  # "ok" or "ng"
    image4_status = Column(String)  # "ok" or "ng"
    
    # Retraining metadata
    is_test_set = Column(Boolean, default=False)
    dataset_paths = Column(String)  # JSON-stringified list of paths to image/label pairs
