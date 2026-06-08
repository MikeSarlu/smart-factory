from flask import Flask, request, jsonify
import sys
import os
import json

# Add root folder to python path to import lambda_function from aws/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aws.lambda_function import lambda_handler

app = Flask(__name__)

@app.route('/telemetry', methods=['POST'])
def telemetry():
    try:
        # Emulate AWS Lambda Proxy Integration Event
        event = {
            'body': request.get_data(as_text=True)
        }
        context = None
        response = lambda_handler(event, context)
        return jsonify(json.loads(response['body'])), response['statusCode']
    except Exception as e:
        print(f"Error in local receiver: {e}")
        return jsonify({"message": "Local Receiver Error", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
