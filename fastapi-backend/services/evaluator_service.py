# services/evaluator_service.py
import os
import yaml
from pathlib import Path
from ultralytics import YOLO
from services.inference import get_active_model_info_from_db

def generate_dataset_yaml(car_models: list):
    """
    Dynamically creates a YOLO dataset.yaml for a list of car models.
    """
    # Use the first model's directory as a temporary home for the YAML
    # or the root dataset directory.
    dataset_root = Path("dataset")
    
    val_paths = []
    for model in car_models:
        # Relative paths from the 'dataset' root
        val_paths.append(f"{model}/test/images")
    
    config = {
        "path": str(dataset_root.resolve()),
        "train": val_paths, # Fallback, though we usually val on 'val'
        "val": val_paths,
        "test": val_paths,
        "names": {
            0: "sealant"
        }
    }
    
    yaml_path = dataset_root / "multi_dataset.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return str(yaml_path)

def evaluate_model_performance(car_model_query: str):
    """
    Runs YOLO validation on the test set of one or more car models.
    Supports comma-separated strings or 'all'.
    """
    dataset_root = Path("dataset")
    
    # 1. Parse car_models list
    if car_model_query.lower() == "all":
        if not dataset_root.exists():
            return {"success": False, "message": "No dataset directory found."}
        car_models = [d for d in os.listdir(dataset_root) if os.path.isdir(dataset_root / d)]
    else:
        # Split by comma and strip whitespace
        car_models = [m.strip() for m in car_model_query.split(",") if m.strip()]

    if not car_models:
        return {"success": False, "message": "No valid car models specified for evaluation."}

    # 2. Check for data in each model
    valid_models = []
    missing_data = []
    for model in car_models:
        test_dir = dataset_root / model / "test" / "images"
        if test_dir.exists() and len(os.listdir(test_dir)) > 0:
            valid_models.append(model)
        else:
            missing_data.append(model)

    if not valid_models:
        return {
            "success": False, 
            "message": f"None of the requested models ({', '.join(car_models)}) have images in their test sets."
        }

    try:
        # 3. Generate Multi-YAML
        yaml_config = generate_dataset_yaml(valid_models)
        
        # 4. Load and Validate
        active_path, _ = get_active_model_info_from_db()
        device = os.getenv("YOLO_DEVICE", "cpu")
        model = YOLO(active_path)
        model.to(device)
        print(f"Starting combined validation for: {', '.join(valid_models)}...")
        
        results = model.val(data=yaml_config, verbose=False, plots=False)
        
        # 5. Extract Combined Metrics
        mAP50 = results.results_dict.get('metrics/mAP50(B)', 0)
        mAP_95 = results.results_dict.get('metrics/mAP50-95(B)', 0)
        precision = results.results_dict.get('metrics/precision(B)', 0)
        recall = results.results_dict.get('metrics/recall(B)', 0)
        
        # 6. Recommendation logic
        suggest_retrain = mAP_95 < 0.70
        status = "CRITICAL" if mAP_95 < 0.50 else "NEEDS IMPROVEMENT" if mAP_95 < 0.70 else "GOOD" if mAP_95 < 0.90 else "EXCELLENT"
        
        recommendation = "I recommend STARTING RETRAINING to improve overall detection accuracy." if suggest_retrain else "The model is performing well across the selected datasets."
        
        # 7. Format Report
        models_str = ", ".join(valid_models)
        skipped_str = f"\n(Skipped due to no data: {', '.join(missing_data)})" if missing_data else ""
        
        report = (
            f"Combined Evaluation Report:\n"
            f"- Datasets Included: {models_str}{skipped_str}\n"
            f"- Overall Status: {status}\n"
            f"- Aggregate mAP@50: {mAP50:.4f}\n"
            f"- Aggregate mAP@50-95: {mAP_95:.4f}\n"
            f"- Precision: {precision:.4f}\n"
            f"- Recall: {recall:.4f}\n\n"
            f"Conclusion: {recommendation}"
        )
        
        return {
            "success": True,
            "report": report,
            "suggest_retrain": suggest_retrain
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during combined evaluation: {str(e)}"
        }
