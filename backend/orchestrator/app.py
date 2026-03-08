from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
from langdetect import detect
import subprocess
import os

import sys

app = Flask(__name__)
# Allow cross-origin requests from the frontend dev server
CORS(app, resources={r"/*": {"origins": "*"}})

# Service URLs - Using loopback ip for Windows stability
TAMIL_CLASSIFIER_URL = "http://127.0.0.1:1000"
SINHALA_CLASSIFIER_URL = "http://127.0.0.1:2000"
SIMILARITY_MATCHER_URL = "http://127.0.0.1:3000"
CREDIBILITY_PREDICTOR_URL = "http://127.0.0.1:4000"


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
    print(f"DEBUG: Processing request for text: '{text[:50]}...'", flush=True)
    sys.stdout.flush()
    
    if not text:
        return jsonify({"error": "Missing or empty 'text' in request"}), 400

    # Detect language only here
    language = detect_language(text)
    print(f"DEBUG: Detected language: {language}", flush=True)
    sys.stdout.flush()

    # Forward to language-specific classifier when available
    classifier_result = None
    try:
        if language == "tamil":
            print(f"DEBUG: Calling Tamil Classifier at {TAMIL_CLASSIFIER_URL}", flush=True)
            sys.stdout.flush()
            resp = requests.post(f"{TAMIL_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            print(f"DEBUG: Tamil response status: {resp.status_code}", flush=True)
            sys.stdout.flush()
            if resp.status_code == 200:
                raw_classifier = resp.json()
                print(f"DEBUG: Tamil raw response: {raw_classifier}", flush=True)
                sys.stdout.flush()
                # Tamil returns 'prediction' (Fake/Real) and 'confidence' (float) inside a 'success' status
                if raw_classifier.get('status') == 'success':
                    classifier_result = {
                        'prediction': raw_classifier.get('prediction', ''),
                        'confidence': raw_classifier.get('confidence', 0.0)
                    }
                else:
                    print(f"DEBUG: Tamil classifier returned non-success status: {raw_classifier.get('status')}", flush=True)
                    sys.stdout.flush()
                    classifier_result = None

        elif language == "sinhala":
            print(f"DEBUG: Calling Sinhala Classifier at {SINHALA_CLASSIFIER_URL}", flush=True)
            sys.stdout.flush()
            resp = requests.post(f"{SINHALA_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            print(f"DEBUG: Sinhala response status: {resp.status_code}", flush=True)
            sys.stdout.flush()
            if resp.status_code == 200:
                raw_classifier = resp.json()
                print(f"DEBUG: Sinhala raw response: {raw_classifier}", flush=True)
                sys.stdout.flush()
                # Sinhala returns 'label' (FAKE/REAL) and 'confidence' (float)
                classifier_result = {
                    'prediction': raw_classifier.get('label', ''),
                    'confidence': raw_classifier.get('confidence', 0.0)
                }
        else:
            print(f"DEBUG: No language-specific classifier for {language}", flush=True)
            sys.stdout.flush()
            classifier_result = None
    except Exception as e:
        print(f"DEBUG: Exception calling classifier: {e}", flush=True)
        sys.stdout.flush()
        classifier_result = None

    # Always call the similarity matcher for any language
    similarity_result = None
    try:
        print(f"DEBUG: Calling Similarity Matcher at {SIMILARITY_MATCHER_URL}", flush=True)
        sys.stdout.flush()
        resp = requests.post(f"{SIMILARITY_MATCHER_URL}/api/verify", json={"claim": text}, timeout=30)
        print(f"DEBUG: Similarity response status: {resp.status_code}", flush=True)
        sys.stdout.flush()
        if resp.status_code == 200:
            similarity_result = resp.json()
            # print(f"DEBUG: Similarity result: {similarity_result}")
    except Exception as e:
        print(f"DEBUG: Exception calling similarity matcher: {e}", flush=True)
        sys.stdout.flush()
        similarity_result = None

    # Call credibility predictor for all requests
    credibility_result = None
    try:
        # Map detected language to what credibility predictor expects (English/Tamil/Sinhala)
        cred_lang = language.capitalize() if language in ["tamil", "sinhala", "english"] else "English"
        
        cred_payload = {
            "past_fake": data.get("past_fake", 0),
            "past_real": data.get("past_real", 0),
            "domain_age_years": data.get("domain_age_years", 0),
            "followers": data.get("followers", 0),
            "language": cred_lang
        }
        print(f"DEBUG: Calling Credibility Predictor at {CREDIBILITY_PREDICTOR_URL} with lang: {cred_lang}", flush=True)
        sys.stdout.flush()
        resp = requests.post(f"{CREDIBILITY_PREDICTOR_URL}/predict", json=cred_payload, timeout=30)
        print(f"DEBUG: Credibility response status: {resp.status_code}", flush=True)
        sys.stdout.flush()
        if resp.status_code == 200:
            credibility_result = resp.json()
            print(f"DEBUG: Credibility raw response: {credibility_result}", flush=True)
            sys.stdout.flush()
            # Pass through the full high-precision result for the frontend
            # The ensemble still gets its normalized values below
    except Exception as e:
        print(f"DEBUG: Exception calling credibility predictor: {e}", flush=True)
        sys.stdout.flush()
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
            if conf > 0.05: # Lower threshold to catch more signals
                is_p_fake = any(x in pred for x in ['fake', 'false', 'නොමඟ', 'අසත්‍ය'])
                # Weighted higher if certainty is high
                weight = 1.0 if conf > 0.8 else 0.7
                signals.append({'is_fake': is_p_fake, 'conf': conf, 'weight': weight, 'source': 'classifier'})

        # 2. Similarity Matcher Signal (Strongest if match found)
        if similarity_result and similarity_result.get('final_verdict'):
            fv = similarity_result.get('final_verdict', '').lower()
            conf = float(similarity_result.get('confidence', 0.0))
            # Only count as a signal if it actually found a match
            if conf > 0.1 and "no match" not in fv:
                is_s_fake = any(x in fv for x in ['fake', 'false', 'අසත්‍ය'])
                # Similarity matches are very strong signals
                signals.append({'is_fake': is_s_fake, 'conf': conf, 'weight': 1.2, 'source': 'similarity'})

        # 3. Credibility Signal (Supporting)
        if credibility_result:
            cl = str(credibility_result.get('prediction_label', '')).lower()
            cs = float(credibility_result.get('credibility_score', 0.0))
            conf = cs / 100.0
            is_c_fake = any(x in cl for x in ['low', 'not', 'un', 'medium', 'අඩු', 'මධ්‍යම'])
            # Only weight credibility significantly if it's very low or very high
            weight = 0.5
            if 'low' in cl: weight = 0.8
            if 'high' in cl: weight = 0.8
            signals.append({'is_fake': is_c_fake, 'conf': conf, 'weight': weight, 'source': 'credibility'})

        if signals:
            fake_score = sum(s['conf'] * s['weight'] for s in signals if s['is_fake'])
            real_score = sum(s['conf'] * s['weight'] for s in signals if not s['is_fake'])
            
            if fake_score > real_score:
                final_prediction = "Fake"
                # Use total weight of fake signals for average confidence
                relevant_weights = sum(s['weight'] for s in signals if s['is_fake'])
                final_confidence = fake_score / relevant_weights if relevant_weights > 0 else 0.0
            elif real_score > fake_score:
                final_prediction = "Real"
                # Use total weight of real signals for average confidence
                relevant_weights = sum(s['weight'] for s in signals if not s['is_fake'])
                final_confidence = real_score / relevant_weights if relevant_weights > 0 else 0.0
            else:
                # Tie break or fallback
                # If there's a tie but we have signals, usually favor the classifier or pick one
                final_prediction = "Unknown"
                final_confidence = 0.0
                
            # Normalize confidence to not exceed 1.0
            final_confidence = min(final_confidence, 1.0)
        else:
            final_prediction = "Unknown"
            final_confidence = 0.0

    except Exception as e:
        print(f"Error in ensemble calculation: {e}")
        final_prediction = 'Unknown'
        final_confidence = 0.0

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
    # Define services using loopback address for consistency
    TAMIL_CLASSIFIER_URL = "http://127.0.0.1:1000"
    SINHALA_CLASSIFIER_URL = "http://127.0.0.1:2000"
    SIMILARITY_MATCHER_URL = "http://127.0.0.1:3000"
    CREDIBILITY_PREDICTOR_URL = "http://127.0.0.1:4000"

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

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
