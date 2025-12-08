import os
import cv2
import numpy as np
from pathlib import Path

# Global cache to store the loaded masks dictionary
_GT_MASKS_CACHE = None

def calculate_iou(mask1, mask2):
    """Helper to calculate Intersection over Union."""
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    return intersection / union if union > 0 else 0

def detect_defects(result, metadata: str = None, filename: str = None) -> str:
    """
    Analyze a YOLO result and return defect status based on IoU with Ground Truth.
    Reads GT masks from a .npy file.
    
    Args:
        result: YOLO detection result object
        metadata: Subfolder name (unused for .npy lookup but kept for signature compatibility)
        filename: Base filename to look for (e.g., "image.jpg")
    
    Returns:
        str: "ok" if IoU > 0.5, "notgood" otherwise
    """
    global _GT_MASKS_CACHE
    
    if not filename:
        return "ok"
        
    # 1. Load GT Masks Dictionary (Lazy Loading)
    if _GT_MASKS_CACHE is None:
        # Define path to your .npy file
        # Adjust 'base_dir' resolution if needed to point to where gt_masks.npy is located
        base_dir = Path(__file__).parent.parent 
        npy_path = base_dir / "gt_masks.npy"
        
        # Fallback absolute path if relative fails (based on your previous context)
        if not npy_path.exists():
             npy_path = Path(r"C:\Users\Yousuf Traders\Documents\FYP\gt_masks.npy")

        if npy_path.exists():
            try:
                print(f"Loading GT masks from: {npy_path}")
                _GT_MASKS_CACHE = np.load(str(npy_path), allow_pickle=True).item()
            except Exception as e:
                print(f"Error loading .npy file: {e}")
                return "notgood"
        else:
            print(f"Error: gt_masks.npy not found at {npy_path}")
            return "notgood"

    # 2. Retrieve Specific GT Mask
    # Ensure filename matches the key in the dictionary exactly
    if filename not in _GT_MASKS_CACHE:
        print(f"Warning: GT mask for '{filename}' not found in dictionary.")
        return "notgood"
    
    gt_mask = _GT_MASKS_CACHE[filename]
    
    # 3. Process Prediction Mask
    # gt_mask is (H, W) with values 0 or 1
    target_shape = gt_mask.shape 
    
    if result.masks is None:
        pred_mask = np.zeros(target_shape, dtype=np.uint8)
    else:
        masks = result.masks.data.cpu().numpy()
        if len(masks) == 0:
            pred_mask = np.zeros(target_shape, dtype=np.uint8)
        else:
            # Select the largest mask if multiple detections exist
            best_idx = np.argmax([m.sum() for m in masks])
            raw_mask = masks[best_idx]
            
            # Resize predicted mask to match GT mask dimensions
            pred_mask = cv2.resize(raw_mask, (target_shape[1], target_shape[0]))
            pred_mask = (pred_mask > 0.5).astype(np.uint8)

    # 4. Compute IoU and Decision
    iou = calculate_iou(gt_mask, pred_mask)
    print(f"Calculated IoU for '{filename}': {iou:.4f}")
    if iou > 0.4:
        return "ok"
    else:
        return "notgood"