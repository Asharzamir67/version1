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
_CURRENT_TRAINING_STATUS = {
    "status": "Idle",
    "stage": "Idle",
    "progress": 0,
    "total_epochs": 0,
    "current_epoch": 0,
    "message": "System is ready for retraining.",
    "car_model": None,
    "last_update": None
}

def get_training_status():
    global _CURRENT_TRAINING_STATUS
    return _CURRENT_TRAINING_STATUS

def update_status(stage, message, progress=0, current_epoch=0, total_epochs=0, car_model=None):
    global _CURRENT_TRAINING_STATUS
    from datetime import datetime
    from services.websocket_service import manager
    
    _CURRENT_TRAINING_STATUS.update({
        "status": "Busy" if stage != "Idle" else "Idle",
        "stage": stage,
        "message": message,
        "progress": progress,
        "current_epoch": current_epoch,
        "total_epochs": total_epochs,
        "car_model": car_model or _CURRENT_TRAINING_STATUS.get("car_model"),
        "last_update": datetime.now().strftime("%H:%M:%S")
    })
    
    # Broadcast to all connected WebSocket clients
    manager.broadcast_sync(_CURRENT_TRAINING_STATUS)

def run_training_pipeline(car_model_query: str):
    db = SessionLocal()
    try:
        update_status("Preparing", f"Initializing dataset for {car_model_query}...", car_model=car_model_query)
        
        # 1. Prepare Dataset
        dataset_root = Path("dataset")
        if car_model_query.lower() == "all":
            models_to_train = [d for d in os.listdir(dataset_root) if os.path.isdir(dataset_root / d)]
        else:
            models_to_train = [m.strip() for m in car_model_query.split(",") if m.strip()]
        
        yaml_path = generate_dataset_yaml(models_to_train)
        
        # 2. Start Training
        update_status("Training", f"Loading base model for {car_model_query}...", progress=10)
        
        # Load the CURRENT active model as a base for fine-tuning
        active_model_record = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        base_weights = active_model_record.model_path if active_model_record else "yolov8n-seg.pt"
        device = os.getenv("YOLO_DEVICE", "cpu")
        model = YOLO(base_weights)
        model.to(device)
        
        epochs = 10
        
        # Callback to update status after each epoch
        def on_train_epoch_end(trainer):
            epoch = trainer.epoch + 1
            percent = 10 + int((epoch / epochs) * 70) # Map 10-80% to training stage
            update_status("Training", f"Training {car_model_query}: Epoch {epoch}/{epochs}", 
                          progress=percent, current_epoch=epoch, total_epochs=epochs)

        model.add_callback("on_train_epoch_end", on_train_epoch_end)

        # Run training
        results = model.train(
            data=yaml_path,
            epochs=epochs,
            imgsz=640,
            batch=8,
            project="runs/retrain",
            name=car_model_query.replace(",", "_"),
            exist_ok=True,
            verbose=False
        )
        
        new_weights_path = str(Path(results.save_dir) / "weights" / "best.pt")
        
        # 3. Evaluate the New "Challenger" Model
        update_status("Evaluating", "Validating new model performance...", progress=85)
        eval_results = model.val(data=yaml_path, verbose=False)
        
        new_map = eval_results.results_dict.get('metrics/mAP50-95(B)', 0)
        new_precision = eval_results.results_dict.get('metrics/precision(B)', 0)
        new_recall = eval_results.results_dict.get('metrics/recall(B)', 0)
        
        # 4. Champion vs. Challenger Logic
        update_status("Evaluating", "Comparing Challenger vs Champion...", progress=95)
        current_active = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        current_map = current_active.map_50_95 if current_active else 0
        
        is_promotion = new_map > current_map
        
        # Save new model to registry
        new_version_num = (db.query(ModelVersion).count() + 1)
        display_name = "Complete" if car_model_query.lower() == "all" else car_model_query
        
        new_model_entry = ModelVersion(
            car_model_name=display_name,
            version_number=new_version_num,
            model_path=new_weights_path,
            map_50_95=new_map,
            precision=new_precision,
            recall=new_recall,
            is_active=False
        )
        db.add(new_model_entry)
        db.flush() 

        if is_promotion:
            final_msg = f"PROMOTED: v{new_version_num} (mAP {new_map:.4f} > {current_map:.4f})"
            if current_active:
                current_active.is_active = False
            new_model_entry.is_active = True
            db.commit()
            reload_active_model()
            update_status("Idle", f"Success: {final_msg}", progress=100)
        else:
            final_msg = f"REJECTED: v{new_version_num} (mAP {new_map:.4f} <= {current_map:.4f})"
            db.commit()
            update_status("Idle", f"Completed: {final_msg}", progress=100)

    except Exception as e:
        print(f"❌ Training Error: {str(e)}")
        update_status("Idle", f"Error: {str(e)}", progress=0)
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
