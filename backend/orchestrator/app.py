from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
from langdetect import detect
import subprocess
import os

app = Flask(__name__)
# Allow cross-origin requests from the frontend dev server
CORS(app, resources={r"/*": {"origins": "*"}})

# Service URLs
TAMIL_CLASSIFIER_URL = "http://localhost:1000"
SINHALA_CLASSIFIER_URL = "http://localhost:2000"
SIMILARITY_MATCHER_URL = "http://localhost:3000"
CREDIBILITY_PREDICTOR_URL = "http://localhost:4000"

def detect_language(text):
    """Detect language with a quick Unicode-range check for Tamil/Sinhala,
    then fall back to `langdetect` for other languages.
    This improves detection for short native-script inputs.
    """
    # Tamil Unicode block: U+0B80–U+0BFF
    if re.search("[\u0B80-\u0BFF]", text):
        return "tamil"

    # Sinhala Unicode block: U+0D80–U+0DFF
    if re.search("[\u0D80-\u0DFF]", text):
        return "sinhala"

    # Fallback to langdetect for other languages
    try:
        lang = detect(text)
        if lang == "ta":
            return "tamil"
        elif lang == "si":
            return "sinhala"
        else:
            return lang
    except Exception:
        return "unknown"

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
    # Define services to start
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    services = [
        {
            "cwd": os.path.join(project_root, "backend", "sinhala_classifier"),
            "command": [os.path.join(project_root, "backend", "sinhala_classifier", ".venv", "Scripts", "python.exe"), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2000"]
        },
        {
            "cwd": os.path.join(project_root, "backend", "similarity_matcher"),
            "command": [os.path.join(project_root, "backend", "similarity_matcher", "venv", "Scripts", "python.exe"), "app.py"]
        },
        {
            "cwd": os.path.join(project_root, "backend", "tamil_classifier"),
            "command": [os.path.join(project_root, "backend", "tamil_classifier", "venv", "Scripts", "python.exe"), "main.py"]
        },
        {
            "cwd": os.path.join(project_root, "backend", "credibility_predictor"),
            "command": [os.path.join(project_root, "backend", "credibility_predictor", "venv", "Scripts", "python.exe"), "app.py"]
        }
    ]
    
    # Optionally start other microservices. Set ORCHESTRATOR_START_SERVICES=0
    # in the environment to prevent auto-starting (useful for local testing).
    if os.environ.get("ORCHESTRATOR_START_SERVICES", "1") == "1":
        for service in services:
            subprocess.Popen(service["command"], cwd=service["cwd"])
    
    # Run the orchestrator
    app.run(host="0.0.0.0", port=5000, debug=True)