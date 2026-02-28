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


def detect_language(text: str) -> str:
    """Detect language with a quick Unicode-range check for Tamil/Sinhala,
    then fall back to `langdetect` for other languages.
    """
    if not text or not isinstance(text, str):
        return "unknown"

    # Tamil Unicode block: U+0B80–U+0BFF
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "tamil"

    # Sinhala Unicode block: U+0D80–U+0DFF
    if re.search(r"[\u0D80-\u0DFF]", text):
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
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing or empty 'text' in request"}), 400

    # Detect language only here
    language = detect_language(text)

    # Forward to language-specific classifier when available
    classifier_result = None
    try:
        if language == "tamil":
            resp = requests.post(f"{TAMIL_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            if resp.status_code == 200:
                classifier_result = resp.json()
                # Normalize Tamil response: it has 'prediction' and 'confidence'
                if 'prediction' in classifier_result:
                    classifier_result = {
                        'prediction': classifier_result['prediction'],
                        'confidence': classifier_result.get('confidence', 0.0)
                    }

        elif language == "sinhala":
            resp = requests.post(f"{SINHALA_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            if resp.status_code == 200:
                classifier_result = resp.json()
                # Normalize Sinhala response: it has 'label' and 'confidence'
                if 'label' in classifier_result:
                    classifier_result = {
                        'prediction': classifier_result['label'],
                        'confidence': classifier_result.get('confidence', 0.0)
                    }
        else:
            # unknown or other languages: do not call language-specific classifiers
            classifier_result = None
    except Exception:
        classifier_result = None

    # Always call the similarity matcher for any language
    similarity_result = None
    try:
        resp = requests.post(f"{SIMILARITY_MATCHER_URL}/api/verify", json={"claim": text}, timeout=30)
        if resp.status_code == 200:
            similarity_result = resp.json()
    except Exception:
        similarity_result = None

    # Call credibility predictor for all requests
    credibility_result = None
    try:
        cred_payload = {
            "past_fake": data.get("past_fake", 0),
            "past_real": data.get("past_real", 0),
            "domain_age_years": data.get("domain_age_years", 0),
            "followers": data.get("followers", 0),
            "language": language
        }
        resp = requests.post(f"{CREDIBILITY_PREDICTOR_URL}/predict", json=cred_payload, timeout=30)
        if resp.status_code == 200:
            credibility_result = resp.json()
            # Normalize credibility response: 'prediction_label' -> 'credibility', 'credibility_score' -> 'confidence' (0-1)
            if 'prediction_label' in credibility_result:
                credibility_result = {
                    'credibility': credibility_result['prediction_label'],
                    'confidence': credibility_result.get('credibility_score', 0.0) / 100.0
                }
    except Exception:
        credibility_result = None

    # Analysis-based ensemble for final prediction
    final_prediction = "Unknown"
    final_confidence = 0.0

    try:
        signals = []
        
        # 1. Linguistic Classifier Signal (Strong)
        if classifier_result and classifier_result.get('prediction'):
            pred = str(classifier_result.get('prediction')).lower()
            conf = float(classifier_result.get('confidence', 0.0))
            if conf > 0.1:
                is_p_fake = ('fake' in pred or 'false' in pred)
                # Weighted higher if certainty is high
                weight = 1.0 if conf > 0.8 else 0.7
                signals.append({'is_fake': is_p_fake, 'conf': conf, 'weight': weight, 'source': 'classifier'})

        # 2. Similarity Matcher Signal (Strongest if match found)
        if similarity_result and similarity_result.get('final_verdict'):
            fv = similarity_result.get('final_verdict', '').lower()
            conf = similarity_result.get('confidence', 0.0)
            # Only count as a signal if it actually found a match
            if conf > 0.1 and "no match" not in fv:
                is_s_fake = ('false' in fv or 'fake' in fv)
                # Similarity matches are very strong signals
                signals.append({'is_fake': is_s_fake, 'conf': conf, 'weight': 1.2, 'source': 'similarity'})

        # 3. Credibility Signal (Supporting)
        if credibility_result and credibility_result.get('credibility'):
            cl = credibility_result.get('credibility', '').lower()
            conf = credibility_result.get('confidence', 0.0)
            is_c_fake = ('low' in cl or 'not' in cl or 'un' in cl or 'medium' in cl)
            # Only weight credibility significantly if it's very low or very high
            weight = 0.5
            if 'low' in cl: weight = 0.8
            if 'high' in cl: weight = 0.8
            signals.append({'is_fake': is_c_fake, 'conf': conf, 'weight': weight, 'source': 'credibility'})

        if signals:
            fake_score = sum(s['conf'] * s['weight'] for s in signals if s['is_fake'])
            real_score = sum(s['conf'] * s['weight'] for s in signals if not s['is_fake'])
            total_weight = sum(s['weight'] for s in signals)
            
            if fake_score > real_score:
                final_prediction = "Fake"
                final_confidence = fake_score / sum(s['weight'] for s in signals if s['is_fake'])
            elif real_score > fake_score:
                final_prediction = "Real"
                final_confidence = real_score / sum(s['weight'] for s in signals if not s['is_fake'])
            else:
                # Tie break or fallback
                final_prediction = "Unknown"
                final_confidence = 0.0
                
            # Normalize confidence to not exceed 100% (though weighted averages naturally stay within range)
            final_confidence = min(final_confidence, 1.0)
        else:
            final_prediction = "Unknown"

    except Exception as e:
        print(f"Error in ensemble calculation: {e}")
        final_prediction = 'Unknown'

    result = {
        "language": language,
        "classifier": classifier_result,
        "similarity": similarity_result,
        "credibility": credibility_result,
        "final_prediction": final_prediction,
        "final_confidence": round(final_confidence, 4)
    }

    return jsonify(result), 200


if __name__ == "__main__":
    # Define services to start (paths assume repo layout). Set ORCHESTRATOR_START_SERVICES=0 to skip.
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

    if os.environ.get("ORCHESTRATOR_START_SERVICES", "1") == "1":
        for service in services:
            try:
                subprocess.Popen(service["command"], cwd=service["cwd"])
            except Exception:
                # best-effort; orchestrator should still run even if child services fail to start
                pass

    app.run(host="0.0.0.0", port=5000, debug=True)