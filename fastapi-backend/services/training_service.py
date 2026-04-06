# services/training_service.py
import os
import threading
from pathlib import Path
from ultralytics import YOLO
from database import SessionLocal
from models.model_registry import ModelVersion
from services.evaluator_service import generate_dataset_yaml, evaluate_model_performance
from services.inference import reload_active_model, AI_MODEL_DIR

# Global lock to prevent multiple concurrent trainings
_TRAINING_LOCK = threading.Lock()
_CURRENT_TRAINING_STATUS = "Idle"

def get_training_status():
    global _CURRENT_TRAINING_STATUS
    return _CURRENT_TRAINING_STATUS

def run_training_pipeline(car_model_query: str):
    global _CURRENT_TRAINING_STATUS
    db = SessionLocal()
    try:
        _CURRENT_TRAINING_STATUS = f"Initializing training for {car_model_query}..."
        
        # 1. Prepare Dataset
        dataset_root = Path("dataset")
        if car_model_query.lower() == "all":
            models_to_train = [d for d in os.listdir(dataset_root) if os.path.isdir(dataset_root / d)]
        else:
            models_to_train = [m.strip() for m in car_model_query.split(",") if m.strip()]
        
        yaml_path = generate_dataset_yaml(models_to_train)
        
        # 2. Start Training
        _CURRENT_TRAINING_STATUS = f"Training YOLO model on {car_model_query}..."
        
        # Load the CURRENT active model as a base for fine-tuning
        active_model_record = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        base_weights = active_model_record.model_path if active_model_record else "yolov8n-seg.pt"
        device = os.getenv("YOLO_DEVICE", "cpu")
        model = YOLO(base_weights)
        model.to(device)
        
        # Run training
        results = model.train(
            data=yaml_path,
            epochs=10, # Keeping it low for demonstration/stability, normally 50-100
            imgsz=640,
            batch=8,
            project="runs/retrain",
            name=car_model_query.replace(",", "_"),
            exist_ok=True
        )
        
        new_weights_path = str(Path(results.save_dir) / "weights" / "best.pt")
        
        # 3. Evaluate the New "Challenger" Model
        _CURRENT_TRAINING_STATUS = "Evaluating Challenger performance..."
        eval_results = model.val(data=yaml_path, verbose=False)
        
        new_map = eval_results.results_dict.get('metrics/mAP50-95(B)', 0)
        new_precision = eval_results.results_dict.get('metrics/precision(B)', 0)
        new_recall = eval_results.results_dict.get('metrics/recall(B)', 0)
        
        # 4. Champion vs. Challenger Logic
        current_active = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        current_map = current_active.map_50_95 if current_active else 0
        
        is_promotion = new_map > current_map
        
        # Save new model to registry
        new_version_num = (db.query(ModelVersion).count() + 1)
        
        # Naming refinement: 'Complete' for 'all', otherwise use query
        display_name = "Complete" if car_model_query.lower() == "all" else car_model_query
        
        new_model_entry = ModelVersion(
            car_model_name=display_name,
            version_number=new_version_num,
            model_path=new_weights_path,
            map_50_95=new_map,
            precision=new_precision,
            recall=new_recall,
            is_active=False # Default
        )
        db.add(new_model_entry)
        db.flush() 

        if is_promotion:
            _CURRENT_TRAINING_STATUS = f"New Champion Found (mAP: {new_map:.4f} > {current_map:.4f}). Promoting..."
            if current_active:
                current_active.is_active = False
            new_model_entry.is_active = True
            db.commit()
            
            # Hot-reload the inference pool
            reload_active_model()
            _CURRENT_TRAINING_STATUS = f"IDLE - Last training: {car_model_query} PROMOTED (v{new_version_num})"
        else:
            db.commit()
            _CURRENT_TRAINING_STATUS = f"IDLE - Last training: {car_model_query} REJECTED (v{new_version_num}, mAP: {new_map:.4f})"

    except Exception as e:
        print(f"❌ Training Error: {str(e)}")
        _CURRENT_TRAINING_STATUS = f"IDLE - Last training FAILED: {str(e)}"
    finally:
        db.close()

def start_retraining_background(car_model_query: str):
    """Entry point to start the training thread."""
    global _TRAINING_LOCK, _CURRENT_TRAINING_STATUS
    
    if _TRAINING_LOCK.locked():
        return False, "A training task is already in progress."
    
    thread = threading.Thread(target=_run_with_lock, args=(car_model_query,))
    thread.daemon = True
    thread.start()
    return True, f"Training started for {car_model_query} in the background."

def _run_with_lock(car_model_query: str):
    with _TRAINING_LOCK:
        run_training_pipeline(car_model_query)
