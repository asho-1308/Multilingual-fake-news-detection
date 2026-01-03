from flask import Flask, request, jsonify
import requests
import re
from langdetect import detect

app = Flask(__name__)

# Service URLs
TAMIL_CLASSIFIER_URL = "http://tamil-classifier-service:1000"
SINHALA_CLASSIFIER_URL = "http://sinhala-classifier-service:2000"
SIMILARITY_MATCHER_URL = "http://similarity-matcher-service:3000"
CREDIBILITY_PREDICTOR_URL = "http://credibility-predictor-service:4000"

def detect_language(text):
    try:
        lang = detect(text)
        if lang == 'ta':
            return 'tamil'
        elif lang == 'si':
            return 'sinhala'
        else:
            return 'english'  # or other
    except:
        return 'unknown'

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Orchestrator service is running"}), 200

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' in request"}), 400

    text = data["text"].strip()
    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    # Detect language
    language = detect_language(text)

    # Call appropriate classifier
    classifier_result = None
    if language == 'tamil':
        try:
            response = requests.post(f"{TAMIL_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            if response.status_code == 200:
                classifier_result = response.json()
        except:
            pass
    elif language == 'sinhala':
        try:
            response = requests.post(f"{SINHALA_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            if response.status_code == 200:
                classifier_result = response.json()
        except:
            pass

    # Call similarity matcher
    similarity_result = None
    try:
        response = requests.post(f"{SIMILARITY_MATCHER_URL}/api/verify", json={"claim": text}, timeout=30)
        if response.status_code == 200:
            similarity_result = response.json()
    except:
        pass

    # Call credibility predictor (this could be additional logic)
    credibility_result = {"credibility": "unknown", "confidence": 0.0}

    # Combine results
    result = {
        "language": language,
        "classifier": classifier_result,
        "similarity": similarity_result,
        "credibility": credibility_result
    }

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)