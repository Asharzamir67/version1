# controllers/image_controller.py
from fastapi import UploadFile
from typing import List
import base64
from io import BytesIO

def process_images_controller(files: List[UploadFile]):
    if len(files) != 4:
        raise ValueError("Exactly 4 images required")

    # -------------------------------
    # Hardcoded processing logic
    # -------------------------------
    condition_ok = False  # Change to True to test "ok" case

    if condition_ok:
        return {"result": "ok"}
    else:
        processed_images_base64 = []
        for f in files:
            content = f.file.read()
            encoded = base64.b64encode(content).decode("utf-8")
            processed_images_base64.append({"filename": f.filename, "data": encoded})
        return {"result": "notgood", "images": processed_images_base64}
