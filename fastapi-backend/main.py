# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all your routers
from routes import user_routes, admin_routes, image_routes
from database import Base, engine

# -------------------- Create Tables --------------------
# This will create all tables in your RDS/Postgres database if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI MVC Auth & Image Processing",
    description="Backend API with JWT auth, user/admin separation, and image processing",
    version="1.0.0"
)

# -------------------- CORS Setup --------------------
origins = [
    "http://localhost:3000",  # your frontend URL
    "http://127.0.0.1:3000",
    "*"  # optional, allow all origins
]

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- Include Routers --------------------
app.include_router(user_routes.router)
app.include_router(admin_routes.router)
app.include_router(image_routes.router)

# -------------------- Root --------------------
@app.get("/", summary="Root Endpoint")
async def root():
    return {"message": "Welcome to the FastAPI MVC Backend!"}
