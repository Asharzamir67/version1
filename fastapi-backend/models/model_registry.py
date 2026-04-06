from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.sql import func
from database import Base

class ModelVersion(Base):
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True)
    car_model_name = Column(String, index=True) # e.g., 'Corolla' or 'All'
    version_number = Column(Integer, default=1)
    model_path = Column(String) # Path to the .pt file
    
    # Performance metrics
    map_50 = Column(Float, default=0.0)
    map_50_95 = Column(Float, default=0.0)
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
