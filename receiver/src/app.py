#Importación de librerias: Flask crea la API, request captura las peticiones y jsonify devuelve respuestas JSON
from flask import Flask, request, jsonify
import sys
import os
import json

#Agrega la carpeta raíz del proyecto al path de Python para importar los módulos de la carpeta aws/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from aws.lambda_function import lambda_handler as telemetry_handler
from aws.lambda_control import lambda_handler as control_handler

#Inicializa Flask
app = Flask(__name__)

#Endpoint /telemetry que recibe las solicitudes POST del simulador
@app.route('/telemetry', methods=['POST'])
def telemetry():
    try:
        #Se emula el formato de evento de integración de AWS Lambda capturando el cuerpo de la petición en formato de texto
        event = {
            'body': request.get_data(as_text=True)
        }
        
        #Como se ejecuta de manera local, no se requiere el objeto context de AWS
        context = None
        
        #Función handler de la Lambda pasándole el evento y el contexto
        response = telemetry_handler(event, context)
        
        #Convierte el cuerpo de la respuesta de texto JSON a un diccionario de Python y lo retorna junto con el código de estado HTTP original
        return jsonify(json.loads(response['body'])), response['statusCode']
    except Exception as e:
        #Captura y muestra cualquier error ocurrido durante el procesamiento de la petición local
        print(f"Error en el receptor local (telemetría): {e}")
        return jsonify({"message": "Error en el receptor local", "error": str(e)}), 500


#Endpoint /control que recibe comandos de Grafana para los LEDs
@app.route('/control', methods=['POST', 'OPTIONS'])
def control():
    try:
        #Manejar preflight OPTIONS de CORS para que Grafana pueda llamar este endpoint
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            response.headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
            return response, 200

        #Emular el formato de evento de Lambda-API Gateway
        event = {
            'httpMethod': 'POST',
            'body': request.get_data(as_text=True)
        }
        context = None

        #Llamar al handler de control
        response = control_handler(event, context)

        #Construir la respuesta Flask con los headers CORS
        flask_response = jsonify(json.loads(response['body']))
        flask_response.headers['Access-Control-Allow-Origin'] = '*'
        return flask_response, response['statusCode']
    except Exception as e:
        print(f"Error en el receptor local (control): {e}")
        return jsonify({"message": "Error en el receptor local", "error": str(e)}), 500



#Endpoint GET /control/status/<led_id>: el simulador lo consulta para saber el estado actual del LED
@app.route('/control/status/<led_id>', methods=['GET'])
def control_status(led_id):
    """
    Consulta el estado más reciente de un LED en la tabla control_commands.
    Devuelve el último comando registrado para ese LED.
    """
    try:
        import psycopg2
        connection = psycopg2.connect(
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "secretpassword"),
            host=os.environ.get("DB_HOST", "db"),
            port=os.environ.get("DB_PORT", "5432"),
            database=os.environ.get("DB_NAME", "smartfactory")
        )
        cursor = connection.cursor()
        cursor.execute(
            "SELECT state FROM control_commands WHERE led_id = %s ORDER BY command_timestamp DESC LIMIT 1",
            (led_id,)
        )
        row = cursor.fetchone()
        state = int(row[0]) if row else 0
        cursor.close()
        connection.close()
        return jsonify({"led_id": led_id, "state": state}), 200
    except Exception as e:
        print(f"Error consultando estado de {led_id}: {e}")
        return jsonify({"led_id": led_id, "state": 0}), 200


#Arrancar el servidor de desarrollo local
if __name__ == '__main__':
    #El servidor escucha en todas las interfaces de red (0.0.0.0) en el puerto 8080
    app.run(host='0.0.0.0', port=8080)


