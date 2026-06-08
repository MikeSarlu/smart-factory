import os
import json
import psycopg2
from psycopg2 import Error

# Leer configuraciones desde variables de entorno
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "smartfactory")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

def lambda_handler(event, context):
    try:
        # Extraer el cuerpo de la petición si viene de API Gateway
        if 'body' in event:
            payload = json.loads(event['body'])
        else:
            payload = event # Prueba directa
            
        timestamp = payload.get('timestamp')
        device_id = payload.get('device_id')
        telemetry = payload.get('telemetry', {})
        
        # Validar payload básico
        if not timestamp or not device_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing timestamp or device_id"})
            }
            
        # Conectar a la base de datos PostgreSQL
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        
        cursor = connection.cursor()
        
        insert_query = """
            INSERT INTO telemetry_data 
            (device_id, timestamp, analog_ch1, analog_ch2, digital_ch1, digital_ch2, digital_ch3, digital_ch4, digital_ch5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        record_to_insert = (
            device_id, 
            timestamp, 
            telemetry.get('analog_ch1'), 
            telemetry.get('analog_ch2'),
            telemetry.get('digital_ch1'),
            telemetry.get('digital_ch2'),
            telemetry.get('digital_ch3'),
            telemetry.get('digital_ch4'),
            telemetry.get('digital_ch5')
        )
        
        cursor.execute(insert_query, record_to_insert)
        connection.commit()
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Telemetry data stored successfully"})
        }

    except (Exception, Error) as error:
        print("Error PostgreSQL:", error)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"})
        }
    finally:
        if 'connection' in locals() and connection:
            cursor.close()
            connection.close()
