# services/inference.py
from ultralytics import YOLO
from services.image_utils import bytes_to_image
from pathlib import Path
import os
import queue
import cv2
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

from database import SessionLocal
from models.model_registry import ModelVersion

DEFAULT_MODEL_NAME = "yoloseg_bestwithoutNG.pt"
AI_MODEL_DIR = Path(__file__).resolve().parent.parent / "ai_model"

def get_active_model_info_from_db():
    """Retrieves the path and name of the currently active model from the registry."""
    db = SessionLocal()
    try:
        active_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        if active_model:
            return active_model.model_path, active_model.car_model_name
        
        # Seed logic: If no active model, check if default exists and create a record
        default_path = str(AI_MODEL_DIR / DEFAULT_MODEL_NAME)
        if os.path.exists(default_path):
            new_version = ModelVersion(
                car_model_name="All",
                model_path=default_path,
                is_active=True,
                map_50_95=0.85 # Assume baseline
            )
            db.add(new_version)
            db.commit()
            return default_path, "All"
            
        return None, None
    finally:
        db.close()

class ModelPool:
    def __init__(self, size=4):
        self.size = size
        self.queue = queue.Queue()
        self.current_path = None
        self.initialized = False

    def _ensure_active_path(self):
        """Helper to get path without loading models."""
        if not self.current_path:
            path, _ = get_active_model_info_from_db()
            self.current_path = path
        return self.current_path

    def reload(self):
        """Resets the pool so models are re-loaded on the next request."""
        path, name = get_active_model_info_from_db()
        if not path:
            print("⚠️ WARNING: No active model found.")
            return

        print(f"♻️ ModelPool scheduled for reload: {path}")
        
        # Clear existing queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        
        self.current_path = path
        self.initialized = False # This forces _initialize() on next get_model()

    def _initialize(self):
        """Actual heavy lifting: loads models into memory."""
        if self.initialized:
            return

        path = self._ensure_active_path()
        if not path:
            return

        device = os.getenv("YOLO_DEVICE", "cpu")
        print(f"🚀 Lazy Loading ModelPool ({self.size} instances) on {device}: {path}")
        
        for i in range(self.size):
            # Load model and move to specified device
            model = YOLO(path)
            model.to(device)
            self.queue.put(model)
        
        self.initialized = True

    @contextmanager
    def get_model(self):
        if not self.initialized:
            self._initialize()
            
        model = self.queue.get()
        try:
            yield model
        finally:
            self.queue.put(model)

# Initialize the pool globally (LAZY)
model_pool = ModelPool(size=4)

def reload_active_model():
    """Hook to be called when a new model is promoted."""
    global model_pool
    model_pool.reload()

def run_batch_inference(images_bytes_list: list):
    imgs = [bytes_to_image(b) for b in images_bytes_list]
    resized_imgs = []
    for img in imgs:
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))
        resized_imgs.append(img)

    with model_pool.get_model() as model:
        results = model.predict(
            source=resized_imgs,
            conf=0.25,
            iou=0.5,
            imgsz=640,
            verbose=False,
            save=False
        )
    return results

def run_threaded_inference(images_bytes_list: list):
    def process_and_predict(image_bytes):
        img = bytes_to_image(image_bytes)
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))
            
        with model_pool.get_model() as model:
            res = model.predict(
                source=img,
                conf=0.25,
                iou=0.5,
                imgsz=640,
                verbose=False,
                save=False
            )
            return res[0]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_and_predict, images_bytes_list))
    return results

