from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.user_schema import UserCreate, UserLogin
from controllers.user_controller import register_user, login_user
from utils.dependencies import get_db

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    token = login_user(user, db)
    if not token:
        return {"error": "Invalid credentials"}
    return token
