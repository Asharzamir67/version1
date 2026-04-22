import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Directory for storing saved images and visualized results
SAVED_IMAGES_DIR = BASE_DIR / "saved_images"

# Directory for storing dataset images and labels for retraining
DATASET_DIR = BASE_DIR / "dataset"

# Directory for storing AI model weights (.pt files)
AI_MODEL_DIR = BASE_DIR / "ai_model"

# Default model filename if none is specified or found in database
DEFAULT_MODEL_FILENAME = "yoloseg_bestwithoutNG.pt"

# Standardized status strings for analysis results
STATUS_OK = "ok"
STATUS_NG = "notgood"

# Car model mapping prefixes to directory names
CAR_PREFIX_MAP = {
    "zre": "corolla",
    "nsp": "yaris"
}

# The folder to use if the prefix doesn't match entries in CAR_PREFIX_MAP
STATUS_OTHER = "other"

# Ensure directories exist
def ensure_directories():
    """Creates required data directories if they do not exist."""
    for directory in [SAVED_IMAGES_DIR, DATASET_DIR, AI_MODEL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
