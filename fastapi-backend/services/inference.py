# services/inference.py
from ultralytics import YOLO
from services.image_utils import bytes_to_image
from pathlib import Path

ACTIVE_MODEL_NAME = "yoloseg_bestwithoutNG.pt"
model_path = Path(__file__).resolve().parent.parent / "ai_model" / ACTIVE_MODEL_NAME

# Create a pool of models to be reused across threads
import queue
from contextlib import contextmanager

class ModelPool:
    def __init__(self, model_path, size=4):
        print(f"Initializing ModelPool with {size} instances...")
        self.models = [YOLO(str(model_path)) for _ in range(size)]
        self.queue = queue.Queue()
        for m in self.models:
            self.queue.put(m)

    @contextmanager
    def get_model(self):
        model = self.queue.get()
        try:
            yield model
        finally:
            self.queue.put(model)

# Initialize the pool globally so it persists for the server lifetime
# We use 4 models to match the typical batch size/thread count
model_pool = ModelPool(model_path, size=4)


import cv2

def run_batch_inference(images_bytes_list: list):
    # Kept for reference or fallback
    imgs = [bytes_to_image(b) for b in images_bytes_list]
    
    resized_imgs = []
    for img in imgs:
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))
        resized_imgs.append(img)

    # For batch, we can just grab one model from the pool or use a separate instance
    # But since we are moving to threaded, this might be less relevant.
    # We'll just use one from the pool to be safe.
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
    from concurrent.futures import ThreadPoolExecutor
    
    def process_and_predict(image_bytes):
        # 1. Decode
        img = bytes_to_image(image_bytes)
        
        # 2. Resize
        h, w = img.shape[:2]
        if max(h, w) > 1280:
            scale = 1280 / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))
            
        # 3. Predict
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

    # Run in threads
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_and_predict, images_bytes_list))

    return results

