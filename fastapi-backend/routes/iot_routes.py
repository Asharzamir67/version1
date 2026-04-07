# routes/iot_routes.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header, BackgroundTasks, Form
from typing import Optional
import time
import io
import asyncio
from services.inference import run_threaded_inference
from services.defect_detector import detect_defects
from services.record_service import record_inference_task

router = APIRouter(prefix="/iot", tags=["IoT"])

# For demonstration, we use a simple static API Key. 
# In a real app, this would be stored in the DB/Environment.
IOT_API_KEY = "sealant_iot_device_secret_2024"

async def verify_iot_key(x_api_key: str = Header(...)):
    if x_api_key != IOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid IoT API Key")
    return True

@router.post("/push", summary="High-speed endpoint for IoT device image pushes")
async def iot_push_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    car_model: str = Form("IOT_DEFAULT"),
    metadata: str = Form("{}"),
    authorized: bool = Depends(verify_iot_key)
):
    """
    Accepts a single image from an IoT device, runs inference,
    and offloads recording to the background.
    """
    start_time = time.time()
    
    # Read image
    img_bytes = await image.read()
    
    # IoT devices usually push 1 by 1, but our engine likes lists (batches)
    file_bytes = [img_bytes]
    
    # 1. Run YOLO
    results = run_threaded_inference(file_bytes)
    
    # 2. Run Defect Detection
    defect_status = detect_defects(results[0], metadata, image.filename)
    
    # 3. Offload all I/O to Background
    # We mock a 4-image batch structure for the record_service by padding if needed, 
    # but for now, we'll just pass a 1-image batch.
    # Note: record_service expects 4 statuses, we provide 1 and 3 'N/A'
    background_tasks.add_task(
        record_inference_task,
        rendered_images=[(image.filename, results[0].plot(boxes=False).tobytes())], # Rendered on demand
        file_bytes=file_bytes,
        results=results,
        model=car_model,
        defect_statuses=[defect_status, "N/A", "N/A", "N/A"],
        original_filenames=[image.filename]
    )

    total_latency = time.time() - start_time
    
    return {
        "status": "success",
        "defect_detected": defect_status != "No Defects",
        "details": defect_status,
        "latency_ms": int(total_latency * 1000)
    }
