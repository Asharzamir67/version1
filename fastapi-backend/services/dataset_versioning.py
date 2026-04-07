# services/dataset_versioning.py
import os
import shutil
import yaml
from pathlib import Path
from datetime import datetime

DATASET_ROOT = Path("dataset")

def create_dataset_snapshot(version_name=None):
    """
    Creates a versioned snapshot of the current 'dataset' folder.
    Structure:
    dataset_versions/
        v1_20240406/
            train/
            test/
            data.yaml
    """
    if not DATASET_ROOT.exists():
        return {"error": "No dataset found to snapshot."}

    # 1. Define Version Name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not version_name:
        version_name = f"v_{timestamp}"
    
    version_dir = Path("dataset_versions") / version_name
    version_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy current dataset contents to versioned folder
    # We iterate through car models in the dataset root
    car_models = [d for d in DATASET_ROOT.iterdir() if d.is_dir()]
    
    for model_path in car_models:
        model_name = model_path.name
        dest_path = version_dir / model_name
        shutil.copytree(model_path, dest_path, dirs_exist_ok=True)

    # 3. Generate data.yaml for YOLO training
    # We simplify this to assume all car models are classes for now, 
    # or just use a generic 'sealant' class as defined in dataset_service.
    data_config = {
        "train": str(version_dir.absolute()), # This usually needs to point to the images subfolders
        "val": str(version_dir.absolute()),   # For simplicity in this project, we point to the root
        "nc": 1,
        "names": ["sealant"]
    }

    with open(version_dir / "data.yaml", "w") as f:
        yaml.dump(data_config, f, default_flow_style=False)

    return {
        "message": "Snapshot created successfully",
        "version": version_name,
        "path": str(version_dir)
    }

def list_snapshots():
    versions_root = Path("dataset_versions")
    if not versions_root.exists():
        return []
    return [d.name for d in versions_root.iterdir() if d.is_dir()]
