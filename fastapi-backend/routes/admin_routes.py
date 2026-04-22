from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.admin_schema import AdminCreate, AdminLogin, ChatContextRequest
from controllers.admin_controller import register_admin, login_admin
from utils.dependencies import get_db, get_current_admin
from agents.model_agent import get_current_model_status
from models.inference_result import InferenceResult
from models.model_registry import ModelVersion
from sqlalchemy import func, and_, cast, Date
import os
import subprocess
from datetime import datetime, timedelta
from config import DATASET_DIR, SAVED_IMAGES_DIR, STATUS_OK, STATUS_NG

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/register")
def register(admin: AdminCreate, db: Session = Depends(get_db)):
    return register_admin(admin, db)

@router.post("/login")
def login(admin: AdminLogin, db: Session = Depends(get_db)):
    token = login_admin(admin, db)
    if not token:
        return {"error": "Invalid credentials"}
    return token

# Example admin-protected route
@router.get("/dashboard")
def dashboard(current_admin=Depends(get_current_admin)):
    return {"message": f"Welcome {current_admin.username} to admin dashboard!"}

@router.post("/model-status")
def model_status(request: ChatContextRequest, db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    # Convert history items to dicts for the agent
    history = [m.dict() for m in request.history] if request.history else []
    # Ensure prompt is never None to avoid Pydantic validation errors in LangChain
    prompt = request.prompt or "Summarize the current system status."
    status_data = get_current_model_status(db, prompt=prompt, history=history)
    return status_data

# --- User Management Routes ---
from typing import List, Optional
from schemas.user_schema import UserResponse, UserUpdate
from controllers.admin_controller import get_all_users, update_user, delete_user
from fastapi import HTTPException

@router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    return get_all_users(db)

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_route(user_id: int, user: UserUpdate, db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    updated_user = update_user(user_id, user, db)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.delete("/users/{user_id}")
def delete_user_route(user_id: int, db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    success = delete_user(user_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.get("/daily-stats")
def get_daily_stats(db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    """Fetch total OK and NG counts for the last 7 days from the inference_results table."""
    try:
        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        # We'll use a dictionary to store stats by date for easy lookup
        stats_map = { (start_date + timedelta(days=i)).strftime("%Y-%m-%d"): {"ok": 0, "ng": 0} for i in range(7) }
        
        # Efficiently query only the status columns within the date range
        results = db.query(
            cast(InferenceResult.input_time, Date).label("date"),
            InferenceResult.image1_status,
            InferenceResult.image2_status,
            InferenceResult.image3_status,
            InferenceResult.image4_status
        ).filter(
            cast(InferenceResult.input_time, Date) >= start_date
        ).all()
        
        # Aggregate the counts
        for row in results:
            date_str = row.date.strftime("%Y-%m-%d")
            if date_str in stats_map:
                # Sum OK/NG across all 4 images in the row
                statuses = [row.image1_status, row.image2_status, row.image3_status, row.image4_status]
                for s in statuses:
                    if s:
                        s_lower = s.lower()
                        if s_lower == STATUS_OK:
                            stats_map[date_str]["ok"] += 1
                        elif s_lower == STATUS_NG or s_lower == 'ng':
                            stats_map[date_str]["ng"] += 1
        
        # Convert map back to an ordered list for the chart
        return [{"date": d, "ok": s["ok"], "ng": s["ng"]} for d, s in sorted(stats_map.items())]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dataset-stats")
def get_dataset_stats(db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    """Fetch counts of training and testing images for each car model."""
    try:
        # 1. Start with car models found in the database
        car_models = db.query(InferenceResult.car_model).distinct().all()
        models = [m[0] for m in car_models if m[0]]
        
        # 2. Check filesystem for all available models in the dataset folder
        if DATASET_DIR.exists():
            for model_folder in os.listdir(DATASET_DIR):
                if (DATASET_DIR / model_folder).is_dir() and model_folder not in models:
                    models.append(model_folder)
        
        results = []
        for model in models:
            # Query DB for counts
            train_db = db.query(func.count(InferenceResult.id)).filter(
                and_(InferenceResult.car_model == model, InferenceResult.is_test_set == False)
            ).scalar()
            test_db = db.query(func.count(InferenceResult.id)).filter(
                and_(InferenceResult.car_model == model, InferenceResult.is_test_set == True)
            ).scalar()
            
            # Query Filesystem for physical image counts
            train_fs = 0
            test_fs = 0
            model_path = DATASET_DIR / model
            if model_path.exists():
                for split, count_ref in [("train", "train_fs"), ("test", "test_fs")]:
                    split_path = model_path / split / "images"
                    if split_path.exists():
                        count = len([f for f in os.listdir(split_path) if f.endswith(('.jpg', '.jpeg', '.png'))])
                        if split == "train": train_fs = count
                        else: test_fs = count
            
            results.append({
                "model": model,
                "train": train_fs or train_db or 0,
                "test": test_fs or test_db or 0
            })
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-registry")
def get_model_registry(db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    """Fetch all model versions recorded in the system."""
    try:
        versions = db.query(ModelVersion).order_by(ModelVersion.version_number.desc()).all()
        return [{
            "version": v.version_number,
            "car_model": v.car_model_name,
            "map": v.map_50_95,
            "is_active": v.is_active,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M"),
            "training_data": v.car_model_name # In this system, car_model_name represents the training scope
        } for v in versions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Dataset Management ---
from services.dataset_versioning import create_dataset_snapshot, list_snapshots

@router.post("/dataset/snapshot")
def snapshot_dataset(version_name: Optional[str] = None, current_admin=Depends(get_current_admin)):
    """Create a versioned snapshot of the current dataset."""
    result = create_dataset_snapshot(version_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/dataset/versions")
def get_dataset_versions(current_admin=Depends(get_current_admin)):
    """List all available dataset snapshots."""
    return {"versions": list_snapshots()}


@router.post("/open-images-folder")
def open_images_folder(current_admin=Depends(get_current_admin)):
    """Open the local saved_images folder on the host machine."""
    folder_path = str(SAVED_IMAGES_DIR.resolve())
    if not SAVED_IMAGES_DIR.exists():
        SAVED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Cross-platform folder opening
        if os.name == 'nt': # Windows
            os.startfile(folder_path)
        elif os.name == 'posix': # macOS or Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', folder_path])
        return {"message": "Folder opened"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
