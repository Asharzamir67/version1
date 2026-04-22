import requests
import os
import time
import json

# Configuration
API_URL = "http://localhost:8000/iot/push"
API_KEY = "sealant_iot_device_secret_2024"
# Use relative path from the simulator script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, "fastapi-backend", "saved_images")

def simulate_iot_push():
    print("--- Sealant IoT Simulator Starting ---")
    
    # 1. Find some images to send (using previously saved ones as mock captures)
    if not os.path.exists(IMAGE_FOLDER):
        print(f"Error: No images found at {IMAGE_FOLDER} to simulate with.")
        return

    # Look for the first image in any subfolder
    target_img = None
    for root, dirs, files in os.walk(IMAGE_FOLDER):
        for file in files:
            if file.endswith((".jpg", ".jpeg", ".png")):
                target_img = os.path.join(root, file)
                break
        if target_img: break

    if not target_img:
        print("Error: Could not find any JPG/PNG images to simulate a push.")
        return

    print(f"Device: Found mock capture: {os.path.basename(target_img)}")

    # 2. Prepare the Request
    files = {
        'image': (os.path.basename(target_img), open(target_img, 'rb'), 'image/jpeg')
    }
    data = {
        'car_model': 'IoT_Mock_Cam_01',
        'metadata': json.dumps({"battery": "85%", "location": "Station_B"})
    }
    headers = {
        "X-API-KEY": API_KEY
    }

    # 3. Send Push
    print(f"Device: Pushing image to {API_URL}...")
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, files=files, data=data, headers=headers)
        latency = time.time() - start_time
        
        if response.status_code == 200:
            res_data = response.json()
            print(f"\n✅ SUCCESS (Latency: {latency:.3f}s)")
            print(f"Result: {res_data['details']}")
            print(f"Defect Detected: {res_data['defect_detected']}")
            print(f"Backend Internal Latency: {res_data['latency_ms']}ms")
        else:
            print(f"\n❌ FAILED ({response.status_code})")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    simulate_iot_push()
