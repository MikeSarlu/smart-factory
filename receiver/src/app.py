#Importación de librerias: Flask crea la API, request captura las peticiones y jsonify devuelve respuestas JSON
from flask import Flask, request, jsonify
import sys
import os
import json

#Agrega la carpeta raíz del proyecto al path de Python para importar el módulo lambda_function desde la carpeta aws/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aws.lambda_function import lambda_handler

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
        response = lambda_handler(event, context)
        
        #Convierte el cuerpo de la respuesta de texto JSON a un diccionario de Python y lo retorna junto con el código de estado HTTP original
        return jsonify(json.loads(response['body'])), response['statusCode']
    except Exception as e:
        #Captura y muestra cualquier error ocurrido durante el procesamiento de la petición local
        print(f"Error en el receptor local: {e}")
        return jsonify({"message": "Error en el receptor local", "error": str(e)}), 500

#Arrancar el servidor de desarrollo local
if __name__ == '__main__':
    #El servidor escucha en todas las interfaces de red (0.0.0.0) en el puerto 8080
    app.run(host='0.0.0.0', port=8080)

