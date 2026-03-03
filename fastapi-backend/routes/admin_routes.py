from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.admin_schema import AdminCreate, AdminLogin
from controllers.admin_controller import register_admin, login_admin
from utils.dependencies import get_db, get_current_admin
from agents.model_agent import get_current_model_status
from models.inference_result import InferenceResult
from sqlalchemy import func, and_, cast, Date
import os
import subprocess
from datetime import datetime, timedelta

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

@router.get("/model-status")
def model_status(prompt: str = "Summarize the current system status.", db: Session = Depends(get_db), current_admin=Depends(get_current_admin)):
    status_data = get_current_model_status(db, prompt=prompt)
    return status_data

# --- User Management Routes ---
from typing import List
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
                        if s_lower == 'ok':
                            stats_map[date_str]["ok"] += 1
                        elif s_lower == 'notgood' or s_lower == 'ng':
                            stats_map[date_str]["ng"] += 1
        
        # Convert map back to an ordered list for the chart
        return [{"date": d, "ok": s["ok"], "ng": s["ng"]} for d, s in sorted(stats_map.items())]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/open-images-folder")
def open_images_folder(current_admin=Depends(get_current_admin)):
    """Open the local saved_images folder on the host machine."""
    folder_path = os.path.abspath("saved_images")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    try:
        # Cross-platform folder opening
        if os.name == 'nt': # Windows
            os.startfile(folder_path)
        elif os.name == 'posix': # macOS or Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', folder_path])
        return {"message": "Folder opened"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
