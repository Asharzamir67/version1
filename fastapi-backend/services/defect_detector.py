"""
Defect detection service for image processing results.
"""
import os
from pathlib import Path

def detect_defects(result, metadata: str = None, filename: str = None) -> str:
    """
    Analyze a YOLO result and return defect status.
    Reads a reference image from images/{metadata}/{filename}.jpg
    
    Args:
        result: YOLO detection result object
        metadata: Subfolder name in images/ directory (e.g., "batch_001", "production")
        filename: Base filename to look for in the subfolder (with .jpg extension added)
    
    Returns:
        str: "ok" if no defects detected, "notgood" if defects found
    """
    if not metadata or not filename:
        # If metadata or filename not provided, default logic
        if metadata == "defect":
            return "notgood"
        return "ok"
    
    # Build path to reference image
    base_dir = Path(__file__).parent.parent  # Get project root
    images_subfolder = base_dir / "images" / metadata
    
    # Convert filename to jpg if it has a different extension
    filename_without_ext = os.path.splitext(filename)[0]
    reference_image_path = images_subfolder / f"{filename_without_ext}.jpg"
    print(f"Looking for reference image at: {reference_image_path}")
    # Check if reference image exists
    if reference_image_path.exists():
        # TODO: Next step will use this reference image for comparison
        # For now, just return ok
        return "ok"
    else:
        # Reference image not found
        return "notgood"
