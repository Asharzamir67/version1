# services/dataset_service.py
import os
import random
from pathlib import Path

def save_to_dataset(image_bytes, result, car_model, filename, class_id=0, test_split=0.2):
    """
    Saves an image and its YOLO-formatted polygon labels to the dataset folder.
    
    Args:
        image_bytes: Original bytes of the image.
        result: YOLO result object for a single image.
        car_model: Name of the car model for subfolder organization.
        filename: Base filename for the saved files.
        class_id: Default class ID for the labels (default 0 for sealant).
        test_split: Probability of assigning to the test set (default 0.2).
        
    Returns:
        dict: {
            "is_test": bool,
            "image_path": str,
            "label_path": str
        }
    """
    # 1. Determine Split
    is_test = random.random() < test_split
    split_dir = "test" if is_test else "train"
    
    # 2. Define and Create Directory Structure
    # dataset/{car_model}/{split}/images/
    # dataset/{car_model}/{split}/labels/
    from config import DATASET_DIR
    base_dir = DATASET_DIR / car_model / split_dir
    img_dir = base_dir / "images"
    lbl_dir = base_dir / "labels"
    
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean filename (remove extension for label path)
    base_name = os.path.splitext(filename)[0]
    
    # 3. Save Original Image
    img_save_path = img_dir / filename
    with open(img_save_path, "wb") as f:
        f.write(image_bytes)
        
    # 4. Extract and Save Labels (Strict YOLO Polygon Format)
    lbl_save_path = lbl_dir / f"{base_name}.txt"
    yolo_lines = []
    
    if result.masks is not None:
        # result.masks.xyn is a list of [n, 2] arrays of normalized coordinates
        for mask_coords in result.masks.xyn:
            if len(mask_coords) > 0:
                # Flatten the list of [x, y] to [x1, y1, x2, y2, ...]
                coords_str = " ".join([f"{coord:.6f}" for point in mask_coords for coord in point])
                yolo_lines.append(f"{class_id} {coords_str}")
    
    with open(lbl_save_path, "w") as f:
        f.write("\n".join(yolo_lines))
        
    return {
        "is_test": is_test,
        "image_path": str(img_save_path),
        "label_path": str(lbl_save_path)
    }
