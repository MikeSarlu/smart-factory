#Importación para variables de entorno, tiempos, aleatorios, matemáticas y control de subprocesos
import os
import time
import json
import random
import math
import requests
import datetime
import threading

#Configuración del endpoint al que se enviará la telemetría
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8080/telemetry")
#Identificador único del dispositivo
DEVICE_ID = "sensor_block_01"

def generate_telemetry():
    """Genera datos de telemetría simulados para el dispositivo."""
    #Se utiliza la marca de tiempo de Unix como base para las funciones trigonométricas
    t = time.time()
    
    #Canal Analógico 1: Onda senoidal con ruido añadido, entre 0 y 5V
    analog_ch1 = 2.5 + 2.0 * math.sin(t * 0.1) + random.uniform(-0.1, 0.1)
    analog_ch1 = max(0.0, min(5.0, analog_ch1))
    
    #Canal Analógico 2: Onda cosenoidal con diferente frecuencia y ruido, entre 0 y 5V
    analog_ch2 = 2.5 + 1.5 * math.cos(t * 0.05) + random.uniform(-0.2, 0.2)
    analog_ch2 = max(0.0, min(5.0, analog_ch2))
    
    #Canales Digitales: Estados binarios simulados con diferentes comportamientos y probabilidades

    #Canal Digital 1: Simula el estado de encendido/apagado de un motor que cambia cada 10 segundos
    digital_ch1 = 1 if (int(t) % 20) < 10 else 0

    #Canal Digital 2: Estado aleatorio simple
    digital_ch2 = random.choice([0, 1])

    #Canal Digital 3: Alarma que se activa (1) si el canal analógico 1 supera el umbral de 3.0V
    digital_ch3 = 1 if analog_ch1 > 3.0 else 0

    #Canal Digital 4: Canal inactivo fijo en 0
    digital_ch4 = 0

    #Canal Digital 5: Estado de fallo con un 10% de probabilidad de activarse (1)
    digital_ch5 = random.choices([0, 1], weights=[0.9, 0.1])[0]

    #Obtención del timestamp actual
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    #Estructuración de la carga útil de telemetría con valores analógicos redondeados a 2 decimales
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
    """Bucle infinito que genera y envía los datos de telemetría periódicamente."""
    print(f"[{datetime.datetime.now().isoformat()}] Iniciando el simulador de telemetría para el dispositivo {DEVICE_ID}...")
    while True:
        #Generación de la lectura de telemetría
        payload = generate_telemetry()
        print(f"Enviando carga útil: {json.dumps(payload)}")
        
        try:
            #Si el endpoint es válido, se envía la petición POST
            if API_GATEWAY_URL.startswith("http"):
                #Se envía la petición con un límite de tiempo de espera de 5 segundos
                response = requests.post(API_GATEWAY_URL, json=payload, timeout=5)
                print(f"Código de respuesta del receptor: {response.status_code}")
            else:
                print("API_GATEWAY_URL no configurada correctamente. Simulando envío.")
        except Exception as e:
            #Captura cualquier error de conexión o de timeout
            print(f"Error al enviar datos: {e}")
            
        #Espera de 2 segundos antes de generar la siguiente lectura de telemetría
        time.sleep(2)

#Punto de entrada de la aplicación
if __name__ == "__main__":
    #Se inicia el bucle de la simulación en un hilo secundario
    #para permitir que el hilo principal maneje interrupciones sin bloquearse
    simulator_thread = threading.Thread(target=telemetry_loop, daemon=True)
    simulator_thread.start()
    
    #Bucle de espera del hilo principal para mantener la aplicación en ejecución
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        #Finaliza el proceso
        print("Simulador detenido...")

