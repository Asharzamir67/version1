from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from models.inference_result import InferenceResult
from routes import user_routes, admin_routes, image_routes, iot_routes
from contextlib import asynccontextmanager
from config import ensure_directories

# -------------------- Create Tables --------------------
Base.metadata.create_all(bind=engine)

# -------------------- Infrastructure Setup --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    ensure_directories()
    yield
    # Shutdown tasks (if any)

app = FastAPI(
    title="Sealant Monitoring Backend",
    description="Backend API with PWA support, IoT hooks, and background task offloading.",
    version="2.0.0",
    lifespan=lifespan
)

# -------------------- CORS Setup --------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Include Routers --------------------
app.include_router(user_routes.router)
app.include_router(admin_routes.router)
app.include_router(image_routes.router)
app.include_router(iot_routes.router)

# -------------------- Root --------------------
@app.get("/", summary="Root Endpoint")
async def root():
    return {"message": "Welcome to the FastAPI MVC Backend!"}
