import os
import time
import json
import random
import math
import requests
import datetime
import threading

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8080/telemetry")
DEVICE_ID = "sensor_block_01"

def generate_telemetry():
    """Generates simulated telemetry data for the device."""
    # Use time as a base for sine wave to simulate analog signals
    t = time.time()
    
    # Analog 1: Sine wave with some noise, between 0 and 5V
    analog_ch1 = 2.5 + 2.0 * math.sin(t * 0.1) + random.uniform(-0.1, 0.1)
    analog_ch1 = max(0.0, min(5.0, analog_ch1))
    
    # Analog 2: Cosine wave with different frequency and noise
    analog_ch2 = 2.5 + 1.5 * math.cos(t * 0.05) + random.uniform(-0.2, 0.2)
    analog_ch2 = max(0.0, min(5.0, analog_ch2))
    
    # Digital channels: random binary states with probabilities
    # Let's say digital_ch1 is a motor state that toggles rarely
    digital_ch1 = 1 if (int(t) % 20) < 10 else 0
    digital_ch2 = random.choice([0, 1])
    digital_ch3 = 1 if analog_ch1 > 3.0 else 0 # Threshold alarm
    digital_ch4 = 0
    digital_ch5 = random.choices([0, 1], weights=[0.9, 0.1])[0] # Error state, mostly 0
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    payload = {
        "timestamp": timestamp,
        "device_id": DEVICE_ID,
        "telemetry": {
            "analog_ch1": round(analog_ch1, 2),
            "analog_ch2": round(analog_ch2, 2),
            "digital_ch1": digital_ch1,
            "digital_ch2": digital_ch2,
            "digital_ch3": digital_ch3,
            "digital_ch4": digital_ch4,
            "digital_ch5": digital_ch5
        }
    }
    
    return payload

def telemetry_loop():
    print(f"[{datetime.datetime.now().isoformat()}] Starting telemetry simulator for device {DEVICE_ID}...")
    while True:
        payload = generate_telemetry()
        print(f"Sending payload: {json.dumps(payload)}")
        
        try:
            if API_GATEWAY_URL.startswith("http"):
                # Real deployment would send this to the API
                # Timeout added to prevent hanging threads if API is down
                response = requests.post(API_GATEWAY_URL, json=payload, timeout=5)
                print(f"Response status: {response.status_code}")
            else:
                print("API_GATEWAY_URL no configurada correctamente. Simulando envío.")
        except Exception as e:
            print(f"Error enviando datos: {e}")
            
        time.sleep(2) # Enviar datos cada 2 segundos

if __name__ == "__main__":
    # Iniciar la simulación en un hilo (para demostrar concurrencia, aunque aquí el main también podría bloquearse)
    simulator_thread = threading.Thread(target=telemetry_loop, daemon=True)
    simulator_thread.start()
    
    # Mantener el programa vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulador detenido por el usuario.")
