from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List
from utils.dependencies import get_current_user
from services.inference import run_batch_inference, run_threaded_inference
from services.defect_detector import detect_defects
from services.dataset_service import save_to_dataset
from sqlalchemy.orm import Session
from database import SessionLocal
from utils.dependencies import get_db
from models.inference_result import InferenceResult
import asyncio
import cv2
import json
import io
import os
import zipfile
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/process", summary="Upload 4 images and receive a zipped result package")
async def process_images(
    images: List[UploadFile] = File(..., description="Upload 4 images"),
    model: str = Form(...),
    metadata: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if len(images) != 4:
        raise HTTPException(status_code=400, detail="Exactly 4 images required")

    # --- Read files concurrently ---
    start_read = time.time()
    file_bytes = await asyncio.gather(*[img.read() for img in images])
    read_time = time.time() - start_read
    print(f"Received {len(file_bytes)} images for processing. Read time: {read_time:.3f}s")

    # --- Run YOLO inference (Threaded with Model Pool) ---
    start_inference = time.time()
    results = run_threaded_inference(file_bytes)
    inference_time = time.time() - start_inference
    print(f"Threaded Inference completed. Inference time: {inference_time:.3f}s")

    # --- Prepare ZIP file in memory ---
    start_zip = time.time()
    zip_buffer = io.BytesIO()

    summary_output = []  # metadata to include in zip

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_STORED) as zipf:

        # Threaded rendering to speed up numpy→JPEG conversion
        def render_to_jpeg(result, filename):
            rendered = result.plot(boxes=False)

            # Convert numpy → JPEG bytes
            success, buffer = cv2.imencode(".jpg", rendered)
            if not success:
                raise RuntimeError("Failed to encode image.")

            return filename, buffer.tobytes()

        with ThreadPoolExecutor(max_workers=4) as executor:
            rendered_images = list(
                executor.map(
                    lambda r, f: render_to_jpeg(r, f.filename),
                    results,
                    images
                )
            )

        # --- Run Defect Detection concurrently ---
        def run_detection(idx, filename):
            return detect_defects(results[idx], metadata, filename)

        with ThreadPoolExecutor(max_workers=4) as executor:
            defect_statuses = list(
                executor.map(
                    run_detection,
                    range(len(rendered_images)),
                    [f for f, _ in rendered_images]
                )
            )

        # Add rendered JPEGs + metadata to ZIP
        for idx, (filename, jpeg_bytes) in enumerate(rendered_images):
            
            defect_status = defect_statuses[idx]

            summary_output.append({
                "filename": filename,
                #"predictions": results[idx].to_json(),
                "defect": defect_status
            })

            # Store image into zip
            zipf.writestr(f"processed/{filename}", jpeg_bytes)

        # Add metadata JSON to the ZIP
        zipf.writestr("results.json", json.dumps({
            "model": model,
            "metadata": metadata,
            "summary": summary_output
        }, indent=2))

    # --- Save images and record result to DB ---
    save_dir = "saved_images"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{model}"
    full_save_path = os.path.join(save_dir, folder_name)
    os.makedirs(full_save_path)

    for filename, jpeg_bytes in rendered_images:
        img_path = os.path.join(full_save_path, filename)
        with open(img_path, "wb") as f:
            f.write(jpeg_bytes)

    # --- Save Structured Dataset for Retraining (New Logic) ---
    dataset_records = []
    is_test_set_final = False
    
    for idx, (filename, _) in enumerate(rendered_images):
        # We use ORIGINAL file_bytes for retraining, NOT the Plot-rendered bytes
        res = save_to_dataset(
            image_bytes=file_bytes[idx],
            result=results[idx],
            car_model=model,
            filename=images[idx].filename
        )
        dataset_records.append(res)
        # If any of the 4 images in the batch is marked as test, track the batch as test?
        # Alternatively, since they share a single DB entry, we'll mark is_test_set if the first one is.
        if idx == 0:
            is_test_set_final = res["is_test"]

    # Record in Database
    new_result = InferenceResult(
        car_model=model,
        image1_status=defect_statuses[0],
        image2_status=defect_statuses[1],
        image3_status=defect_statuses[2],
        image4_status=defect_statuses[3],
        is_test_set=is_test_set_final,
        dataset_paths=json.dumps(dataset_records)
    )
    db.add(new_result)
    db.commit()
    db.refresh(new_result)

    zip_time = time.time() - start_zip
    total_time = time.time() - start_read
    print(f"ZIP created. Zip+write time: {zip_time:.3f}s; total request time: {total_time:.3f}s")


    # Reset stream for sending
    zip_buffer.seek(0)

    # --- Return ZIP as streaming response ---
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=processed_results.zip"
        }
    )
