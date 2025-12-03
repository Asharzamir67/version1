from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.admin_schema import AdminCreate, AdminLogin
from controllers.admin_controller import register_admin, login_admin
from utils.dependencies import get_db, get_current_admin

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
