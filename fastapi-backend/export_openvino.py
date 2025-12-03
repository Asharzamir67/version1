from ultralytics import YOLO
import os

# Load the model
model_path = r'c:\Users\HP VICTUS\Documents\fastapi_mvc_auth\ai_model\yoloseg_bestwithoutNG.pt'
model = YOLO(model_path)

# Export to OpenVINO
print(f"Exporting model from: {model_path}")
export_path = model.export(format='openvino')
print(f"Model exported to: {export_path}")
print(f"Export path exists: {os.path.exists(export_path)}")
if os.path.isdir(export_path):
    print(f"Contents: {os.listdir(export_path)}")
