from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
from datetime import datetime, date as dt_date
from models.inference_result import InferenceResult
from models.model_registry import ModelVersion
from services.evaluator_service import evaluate_model_performance
from services.training_service import start_retraining_background, get_training_status
from config import SAVED_IMAGES_DIR, DATASET_DIR

def get_system_stats(db: Session):
    """Query the database and filesystem to get total records and image counts. Requires a db session."""
    try:
        db_count = db.query(func.count(InferenceResult.id)).scalar()
        total_images = 0
        if SAVED_IMAGES_DIR.exists():
            for root, dirs, files in os.walk(SAVED_IMAGES_DIR):
                total_images += len([f for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
        return f"Database Records: {db_count}, Total Saved Images: {total_images}"
    except Exception as e:
        return f"Error fetching stats: {str(e)}"

def get_active_model_info(db: Session):
    """Get information about the AI model currently 'Active' in production."""
    try:
        active = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        if active:
            return (f"Active Model: Version {active.version_number} ({active.car_model_name})\n"
                    f"- mAP@50-95: {active.map_50_95:.4f}\n"
                    f"- Path: {active.model_path}\n"
                    f"- Created: {active.created_at.strftime('%Y-%m-%d %H:%M')}")
        return "No model is currently marked as 'Active' in the registry."
    except Exception as e:
        return f"Error fetching active model info: {str(e)}"

def get_car_model_stats(db: Session, model_name: str, only_today: bool = False):
    """
    Count how many cars of a specific model type were processed.
    Args:
        model_name: The name or part of the name of the car model (e.g., 'Toyota', 'Corolla').
        only_today: If True, only count cars processed today.
    """
    try:
        query = db.query(func.count(InferenceResult.id)).filter(
            InferenceResult.car_model.ilike(f"%{model_name}%")
        )
        if only_today:
            today = dt_date.today()
            query = query.filter(func.date(InferenceResult.input_time) == today)
        
        count = query.scalar()
        time_str = "today" if only_today else "in total"
        return f"Found {count} entries for car model '{model_name}' {time_str}."
    except Exception as e:
        return f"Error fetching car model stats: {str(e)}"

def get_retraining_dataset_stats(db: Session):
    """Get the current state of the model retraining dataset (train vs test counts organized by car model)."""
    try:
        # DB Stats
        test_count = db.query(func.count(InferenceResult.id)).filter(InferenceResult.is_test_set == True).scalar()
        train_count = db.query(func.count(InferenceResult.id)).filter(InferenceResult.is_test_set == False).scalar()
        
        # Filesystem Stats
        fs_summary = {}
        if DATASET_DIR.exists():
            for model in os.listdir(DATASET_DIR):
                model_path = DATASET_DIR / model
                if model_path.is_dir():
                    fs_summary[model] = {"train": 0, "test": 0}
                    for split in ["train", "test"]:
                        split_path = os.path.join(model_path, split, "images")
                        if os.path.exists(split_path):
                            fs_summary[model][split] = len([f for f in os.listdir(split_path) if f.endswith('.jpg')])
        
        fs_str = "\n".join([f"  - {m}: {s['train']} train, {s['test']} test images" for m, s in fs_summary.items()])
        return (f"Retraining Dataset Summary:\n"
                f"Database: {train_count} samples for training, {test_count} samples for testing.\n"
                f"Filesystem Storage:\n{fs_str if fs_str else f'  (No model folders found in {DATASET_DIR} yet)'}")
    except Exception as e:
        return f"Error fetching dataset stats: {str(e)}"

def get_quality_analytics(db: Session):
    """Calculate the overall OK/NG classification rate based on image statuses."""
    try:
        results = db.query(
            InferenceResult.image1_status,
            InferenceResult.image2_status,
            InferenceResult.image3_status,
            InferenceResult.image4_status
        ).all()
        
        if not results:
            return "No inference data available to calculate quality stats."
            
        total_checks = len(results) * 4
        ok_count = 0
        for row in results:
            ok_count += sum(1 for status in row if status and status.lower() == 'ok')
        
        ng_count = total_checks - ok_count
        ok_rate = (ok_count / total_checks) * 100
        
        return (f"Quality Analytics: Out of {total_checks} image checks, "
                f"{ok_count} were OK ({ok_rate:.1f}%) and {ng_count} were NG.")
    except Exception as e:
        return f"Error calculating quality stats: {str(e)}"

def analyze_ng_patterns(db: Session, car_model: str = None):
    """
    Advanced Root Cause Analysis: Identifies which camera (Image 1-4) is producing the most NG results.
    Can be filtered by car_model.
    """
    try:
        query = db.query(
            InferenceResult.image1_status,
            InferenceResult.image2_status,
            InferenceResult.image3_status,
            InferenceResult.image4_status
        )
        if car_model:
            query = query.filter(InferenceResult.car_model.ilike(f"%{car_model}%"))
        
        results = query.all()
        if not results:
            return "No data found for the specified pattern analysis."

        cam_stats = {1: 0, 2: 0, 3: 0, 4: 0}
        total_ng = 0
        for row in results:
            for i, status in enumerate(row, 1):
                if status and status.lower() in ['ng', 'notgood']:
                    cam_stats[i] += 1
                    total_ng += 1
        
        if total_ng == 0:
            return "No NG cases found in the current selection."

        report = [f"Pattern Analysis (Total NG: {total_ng}):"]
        for cam, count in cam_stats.items():
            percentage = (count / total_ng) * 100
            report.append(f"  - Camera {cam}: {count} NG cases ({percentage:.1f}%)")
            
        # Add a critical insight
        worst_cam = max(cam_stats, key=cam_stats.get)
        if cam_stats[worst_cam] > (total_ng * 0.5):
            report.append(f"\nCRITICAL INSIGHT: Camera {worst_cam} is responsible for over 50% of the defects. Recommend hardware check.")
            
        return "\n".join(report)
    except Exception as e:
        return f"Error analyzing patterns: {str(e)}"

def get_model_registry_history(db: Session):
    """List all trained model versions, their performance metrics, and deployment status."""
    try:
        versions = db.query(ModelVersion).order_by(ModelVersion.version_number.desc()).all()
        if not versions:
            return "Model registry is empty."
        
        lines = ["Model Registry History:"]
        for v in versions:
            status = "[ACTIVE]" if v.is_active else "[Historical]"
            lines.append(f"{status} v{v.version_number} | {v.car_model_name} | mAP: {v.map_50_95:.4f} | Precision: {v.precision:.4f} | {v.created_at.strftime('%Y-%m-%d')}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching registry history: {str(e)}"

@tool
def start_model_retraining(car_model_query: str):
    """
    Initiate a background training task to create a new model version.
    Args:
        car_model_query: Car model to train on (e.g., 'Corolla' or 'all').
    """
    try:
        # Check training status first
        current = get_training_status()
        if "Training" in current:
            return f"Cannot start retraining. System status: {current}"
            
        success, msg = start_retraining_background(car_model_query)
        return msg
    except Exception as e:
        return f"Error triggering retraining: {str(e)}"

def log_system_observation(db: Session, severity: str, category: str, observation: str):
    """
    Log a persistent observation about the system. 
    Severities: INFO, WARNING, CRITICAL. 
    Categories: MODEL_DRIFT, HARDWARE, DATASET.
    """
    try:
        from models.model_registry import SystemObservation
        from services.notifications import notification_service
        
        new_obs = SystemObservation(
            severity=severity.upper(),
            category=category.upper(),
            observation=observation
        )
        db.add(new_obs)
        db.commit()
        
        # Trigger alert if critical
        if severity.upper() == "CRITICAL":
            notification_service.send_critical_alert(severity, category, observation)
            
        return f"Observation logged and alert sent: [{severity}] {observation}" if severity.upper() == "CRITICAL" else f"Observation logged: [{severity}] {observation}"
    except Exception as e:
        return f"Error logging observation: {str(e)}"

def get_past_observations(db: Session, limit: int = 5):
    """Retrieve the last few system observations to understand historical context."""
    try:
        from models.model_registry import SystemObservation
        obs = db.query(SystemObservation).order_by(SystemObservation.created_at.desc()).limit(limit).all()
        if not obs:
            return "No past observations found."
        
        return "\n".join([f"[{o.created_at.strftime('%m-%d %H:%M')}] {o.severity} - {o.observation}" for o in obs])
    except Exception as e:
        return f"Error fetching observations: {str(e)}"

def audit_system_quality(db: Session):
    """
    Performs a time-series audit to find sudden spikes in NG (No-Good) results.
    Compares the last hour to the last 24 hours.
    """
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(hours=24)

        def get_ng_rate(start_time):
            results = db.query(
                InferenceResult.image1_status,
                InferenceResult.image2_status,
                InferenceResult.image3_status,
                InferenceResult.image4_status
            ).filter(InferenceResult.input_time >= start_time).all()
            
            if not results: return 0.0, 0
            
            total_cars = len(results)
            ng_cars = 0
            for row in results:
                if any(status and status.lower() == 'ng' for status in row):
                    ng_cars += 1
            return (ng_cars / total_cars) * 100, total_cars

        recent_rate, recent_count = get_ng_rate(one_hour_ago)
        daily_rate, daily_count = get_ng_rate(one_day_ago)

        report = [
            f"Quality Audit Report ({now.strftime('%H:%M')}):",
            f"- Last Hour NG Rate: {recent_rate:.1f}% ({recent_count} cars)",
            f"- Last 24h NG Rate: {daily_rate:.1f}% ({daily_count} cars)"
        ]

        if recent_rate > daily_rate * 1.5 and recent_count > 5:
            report.append("\nANOMALY DETECTED: The NG rate has spiked significantly in the last hour compared to the daily average.")
        elif recent_rate < daily_rate * 0.5 and recent_count > 5:
            report.append("\nINSIGHT: Quality has significantly improved in the last hour.")
        else:
            report.append("\nStatus: Quality trends are stable.")

        return "\n".join(report)
    except Exception as e:
        return f"Error auditing quality: {str(e)}"

def get_system_error_logs(lines: int = 20):
    """
    Read the latest entries from alerts.log and kernel.errors.txt to diagnose system failures.
    """
    try:
        files = ["alerts.log", "kernel.errors.txt"]
        output = []
        for file in files:
            if os.path.exists(file):
                with open(file, "r") as f:
                    content = f.readlines()[-lines:]
                    output.append(f"--- {file} (Last {len(content)} lines) ---")
                    output.extend([l.strip() for l in content])
                    output.append("\n")
            else:
                output.append(f"File {file} not found.")
        
        return "\n".join(output) if output else "No log files found."
    except Exception as e:
        return f"Error reading logs: {str(e)}"
