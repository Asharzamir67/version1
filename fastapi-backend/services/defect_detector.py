import numpy as np

def detect_defects(result, metadata: str = None, filename: str = None) -> str:
    """
    Analyze a YOLO result and return defect status based on the area occupied by sealant.
    
    Args:
        result: YOLO detection result object (Ultralytics Results)
        metadata: Optional metadata string
        filename: Original filename
    """
    from config import STATUS_OK, STATUS_NG, CONF_THRESH, COVERAGE_THRESHOLD_OK
    
    # 1. Check if masks exist in the result
    if not hasattr(result, 'masks') or result.masks is None:
        return STATUS_NG
        
    # 2. Extract masks and bounding box confidences
    try:
        # result.masks.data is usually a tensor on GPU/CPU
        masks = result.masks.data.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
    except Exception as e:
        print(f"Error accessing mask/box data: {e}")
        return STATUS_NG

    # 3. Filter masks by confidence threshold
    valid_masks = [masks[i] > 0.5 for i in range(len(confs)) if confs[i] >= CONF_THRESH]

    if not valid_masks:
        return STATUS_NG

    # 4. Combine all valid masks into one binary mask to calculate coverage
    # We use np.any to logical-OR all detected sealant polygons
    combined_mask = np.any(valid_masks, axis=0)
    
    # 5. Calculate ratio of occupied pixels to total pixels in the mask grid
    occupied_pixels = np.sum(combined_mask)
    total_pixels = combined_mask.size
    
    coverage_ratio = occupied_pixels / total_pixels if total_pixels > 0 else 0
    
    # 6. Log coverage for debugging (optional context)
    print(f"Sealant Coverage for '{filename or 'unknown'}': {coverage_ratio*100:.2f}%")

    # 7. Decision: Check against configured coverage threshold
    if coverage_ratio >= COVERAGE_THRESHOLD_OK:
        return STATUS_OK
    else:
        return STATUS_NG
