from flask import Flask, jsonify, request
from flask_cors import CORS 

app = Flask(__name__)
CORS(app)

@app.route('/run-script', methods=['POST'])
def run_script():
    return jsonify({'message': "Yippeee"})

if __name__ == '__main__':
    app.run(port=5000)