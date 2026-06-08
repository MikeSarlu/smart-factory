#Importación de librerías del sistema para variables de entorno y procesamiento JSON
import os
import json

#Importación del controlador de PostgreSQL para Python y su clase de control de errores
import psycopg2
from psycopg2 import Error

#Lectura del archivo .env con la configuración de la base de datos
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "smartfactory")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

#Función principal que procesa la petición de telemetría
def lambda_handler(event, context):
    try:
        #Se obtiene el cuerpo de la petición si la invocación proviene de la API
        if 'body' in event:
            payload = json.loads(event['body'])
        else:
            #En caso de una invocación directa, se utiliza el evento completo
            payload = event
            
        #Extracción de los parámetros principales del payload
        timestamp = payload.get('timestamp')
        device_id = payload.get('device_id')
        telemetry = payload.get('telemetry', {})
        
        #Validación básica para asegurar que los campos obligatorios no estén vacíos
        if not timestamp or not device_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Falta la marca de tiempo (timestamp) o el identificador del dispositivo (device_id)"})
            }
            
        #Conexión con la base de datos
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        
        #Cursor para ejecutar las sentencias SQL en la base de datos
        cursor = connection.cursor()
        
        #Consulta SQL parametrizada para insertar las lecturas en la tabla de datos
        insert_query = """
            INSERT INTO telemetry_data 
            (device_id, timestamp, analog_ch1, analog_ch2, digital_ch1, digital_ch2, digital_ch3, digital_ch4, digital_ch5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        #Organización de los datos extraídos correspondiente a las columnas SQL
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
        
        #Ejecución de la consulta SQL insertando los datos ordenados
        cursor.execute(insert_query, record_to_insert)
        
        #Confirmación de la transacción para guardar los cambios en la base de datos
        connection.commit()
        
        #Respuesta exitosa estructurada
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Datos de telemetria almacenados correctamente"})
        }

    except (Exception, Error) as error:
        #Registro del error de base de datos o de ejecución general
        print("Error en PostgreSQL:", error)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error interno del servidor"})
        }
    finally:
        #Cierra el cursor y la conexión al finalizar
        if 'connection' in locals() and connection:
            cursor.close()
            connection.close()

