# services/record_service.py
import os
import json
from datetime import datetime
from database import SessionLocal
from models.inference_result import InferenceResult
from services.dataset_service import save_to_dataset

def record_inference_task(rendered_images, file_bytes, results, model, defect_statuses, original_filenames):
    """
    Background task to handle all slow I/O operations:
    1. Save rendered images to disk
    2. Save raw images/labels to dataset
    3. Log result to the database
    """
    db = SessionLocal()
    try:
        # 1. Save Rendered Images to Disk (for visualization/audit)
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

        # 2. Save Structured Dataset for Retraining
        dataset_records = []
        is_test_set_final = False
        
        for idx, (filename, _) in enumerate(rendered_images):
            res = save_to_dataset(
                image_bytes=file_bytes[idx],
                result=results[idx],
                car_model=model,
                filename=original_filenames[idx]
            )
            dataset_records.append(res)
            if idx == 0:
                is_test_set_final = res["is_test"]

        # 3. Record in Database
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
        print(f"Background task completed: Recorded inference {new_result.id}")

    except Exception as e:
        print(f"Error in background recording task: {e}")
        db.rollback()
    finally:
        db.close()
