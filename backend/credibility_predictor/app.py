from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Credibility predictor service is running"}), 200

@app.route("/api/predict", methods=["POST"])
def predict():
    # Placeholder for credibility prediction
    data = request.get_json()
    # Implement logic here
    return jsonify({"credibility": "high", "confidence": 0.95})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=True)