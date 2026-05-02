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
TAMIL_CLASSIFIER_URL = os.getenv("TAMIL_CLASSIFIER_URL", "http://127.0.0.1:1000")
SINHALA_CLASSIFIER_URL = os.getenv("SINHALA_CLASSIFIER_URL", "http://127.0.0.1:2000")
SIMILARITY_MATCHER_URL = os.getenv("SIMILARITY_MATCHER_URL", "http://127.0.0.1:3000")
CREDIBILITY_PREDICTOR_URL = os.getenv("CREDIBILITY_PREDICTOR_URL", "http://127.0.0.1:4000")


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


@app.route("/predict_light", methods=["POST"])
def predict_light():
    """Lightweight prediction endpoint for Chrome Extension.
    Only uses Linguistic Classifier and Similarity Matcher.
    Ignores Source Credibility.
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    print(f"DEBUG: Processing LIGHT request for text: '{text[:50]}...'", flush=True)
    sys.stdout.flush()
    
    if not text:
        return jsonify({"error": "Missing or empty 'text' in request"}), 400

    language = detect_language(text)
    print(f"DEBUG: LIGHT detected language: {language}", flush=True)
    sys.stdout.flush()

    if language not in ["tamil", "sinhala"]:
        return jsonify({
            "language": language,
            "final_prediction": "Ignored",
            "final_confidence": 0.0,
            "message": "Chrome extension only supports Tamil and Sinhala."
        }), 200

    # 1. Forward to language-specific classifier
    classifier_result = None
    try:
        if language == "tamil":
            print(f"DEBUG: Calling Tamil Classifier for LIGHT", flush=True)
            resp = requests.post(f"{TAMIL_CLASSIFIER_URL}/predict", json={"text": text}, timeout=15)
            if resp.status_code == 200:
                raw = resp.json()
                print(f"DEBUG: Tamil raw for LIGHT: {raw}", flush=True)
                if raw.get('status') == 'success':
                    classifier_result = {'prediction': raw.get('prediction', ''), 'confidence': raw.get('confidence', 0.0)}
        elif language == "sinhala":
            print(f"DEBUG: Calling Sinhala Classifier for LIGHT", flush=True)
            resp = requests.post(f"{SINHALA_CLASSIFIER_URL}/predict", json={"text": text}, timeout=15)
            if resp.status_code == 200:
                raw = resp.json()
                print(f"DEBUG: Sinhala raw for LIGHT: {raw}", flush=True)
                classifier_result = {'prediction': raw.get('label', ''), 'confidence': raw.get('confidence', 0.0)}
    except Exception as e:
        print(f"DEBUG: Exception in LIGHT classifier call: {e}", flush=True)
        classifier_result = None

    # 2. Call similarity matcher
    similarity_result = None
    try:
        print(f"DEBUG: Calling Similarity Matcher for LIGHT (Port 3000)", flush=True)
        resp = requests.post(f"{SIMILARITY_MATCHER_URL}/api/verify", json={"claim": text}, timeout=60)
        print(f"DEBUG: Similarity response status for LIGHT: {resp.status_code}", flush=True)
        if resp.status_code == 200:
            similarity_result = resp.json()
            print(f"DEBUG: Similarity API Response for LIGHT: {similarity_result}", flush=True)
            if similarity_result.get("used_online_search"):
                print(f"DEBUG: [ORC-LIGHT] Live News API was used! Found {len(similarity_result.get('neighbors', []))} results.", flush=True)
        else:
            print(f"DEBUG: Similarity Matcher returned error {resp.status_code}: {resp.text}", flush=True)
    except Exception as e:
        print(f"DEBUG: Exception in LIGHT similarity call: {e}", flush=True)
        similarity_result = None

    # 3. Simple Ensemble (No Credibility)
    final_prediction = "Unknown"
    final_confidence = 0.0
    signals = []
    
    if classifier_result and classifier_result.get('prediction'):
        pred = str(classifier_result.get('prediction')).lower()
        conf = float(classifier_result.get('confidence', 0.0))
        # Support various labeling formats
        is_p_fake = any(x in pred for x in ['fake', 'false', 'නොමඟ', 'අසත්‍ය'])
        is_p_real = any(x in pred for x in ['real', 'true', 'සත්‍ය'])
        
        if is_p_fake or is_p_real:
            signals.append({'is_fake': is_p_fake, 'conf': conf, 'weight': 1.0})

    if similarity_result and similarity_result.get('neighbors'):
        neighbors = similarity_result['neighbors']
        print(f"DEBUG: [ORC] Found {len(neighbors)} neighbors in similarity response", flush=True)
        best_match = max(neighbors, key=lambda x: x['similarity']) if neighbors else None
        
        if best_match:
            s_conf = float(best_match['similarity'])
            print(f"DEBUG: [ORC] Best similarity match: {s_conf}", flush=True)
            s_verdict = str(best_match.get('verdict', '')).lower()
            
            # Treat "News Article" (from Online Search) as REAL
            is_s_fake = any(x in s_verdict for x in ['fake', 'false', 'අසත්‍ය'])
            # If it's from the online scraper ("News Article"), it's definitely REAL for our signal
            if "news article" in s_verdict or "verified real" in s_verdict:
                is_s_fake = False

            # Even low similarity matches provide a signal if they are from the online search
            # We want to show THEM in the extension even if they don't strongly confirm FAKE/REAL
            s_weight = 2.0 if s_conf > 0.8 else 1.0
            signals.append({'is_fake': is_s_fake, 'conf': s_conf, 'weight': s_weight})
    else:
        print(f"DEBUG: [ORC] No neighbors found in similarity result", flush=True)

    if signals:
        total_weight = sum(s['weight'] for s in signals)
        fake_score = sum(s['conf'] * s['weight'] for s in signals if s['is_fake'])
        real_score = sum(s['conf'] * s['weight'] for s in signals if not s['is_fake'])
        
        print(f"DEBUG: LIGHT Scores - Fake: {fake_score}, Real: {real_score}, Total Weight: {total_weight}", flush=True)
        
        if fake_score > real_score:
            final_prediction = "Fake"
            final_confidence = fake_score / total_weight
        elif real_score > fake_score:
            final_prediction = "Real"
            final_confidence = real_score / total_weight
        else:
            final_prediction = "Unknown"
            final_confidence = 0.0
            
    sys.stdout.flush()
    return jsonify({
        "language": language,
        "final_prediction": final_prediction,
        "final_confidence": round(min(final_confidence, 1.0), 4),
        "classifier": classifier_result,
        "similarity": similarity_result
    }), 200


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    debug_mode = bool(data.get("debug", False))
    debug_info = {}
    print(f"DEBUG: Processing request for text: '{text[:50]}...'", flush=True)
    sys.stdout.flush()
    
    if not text:
        return jsonify({"error": "Missing or empty 'text' in request"}), 400

    # Detect language only here
    language = detect_language(text)
    print(f"DEBUG: Detected language: {language}", flush=True)
    sys.stdout.flush()

    if language not in ["tamil", "sinhala"]:
        return jsonify({
            "error": "Prediction only supported for Tamil and Sinhala.",
            "language": language,
            "final_prediction": "Ignored",
            "final_confidence": 0.0
        }), 200

    # Forward to language-specific classifier when available
    classifier_result = None
    try:
        if language == "tamil":
            print(f"DEBUG: Calling Tamil Classifier at {TAMIL_CLASSIFIER_URL}", flush=True)
            sys.stdout.flush()
            resp = requests.post(f"{TAMIL_CLASSIFIER_URL}/predict", json={"text": text}, timeout=30)
            debug_info['tamil_status'] = resp.status_code
            try:
                debug_info['tamil_text'] = resp.text
            except Exception:
                debug_info['tamil_text'] = '<unreadable body>'
            print(f"DEBUG: Tamil response status: {resp.status_code}", flush=True)
            sys.stdout.flush()
            if resp.status_code == 200:
                raw_classifier = resp.json()
                print(f"DEBUG: Tamil raw response: {raw_classifier}", flush=True)
                debug_info['tamil_json'] = raw_classifier
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
            debug_info['sinhala_status'] = resp.status_code
            try:
                debug_info['sinhala_text'] = resp.text
            except Exception:
                debug_info['sinhala_text'] = '<unreadable body>'
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
        # Pass top_k and mode if provided by the client, defaulting to auto/3
        sim_payload = {
            "claim": text,
            "top_k": data.get("top_k", 3),
            "mode": data.get("mode", "auto")
        }
        resp = requests.post(f"{SIMILARITY_MATCHER_URL}/api/verify", json=sim_payload, timeout=30)
        debug_info['similarity_status'] = resp.status_code
        try:
            debug_info['similarity_text'] = resp.text
        except Exception:
            debug_info['similarity_text'] = '<unreadable body>'
        print(f"DEBUG: Similarity response status: {resp.status_code}", flush=True)
        sys.stdout.flush()
        if resp.status_code == 200:
            similarity_result = resp.json()
            print(f"DEBUG: Similarity result keys: {list(similarity_result.keys()) if similarity_result else 'None'}", flush=True)
            # Ensure neighbors is always a list even if API returns it differently
            if similarity_result and 'neighbors' not in similarity_result and 'similar_sources' in similarity_result:
                similarity_result['neighbors'] = similarity_result['similar_sources']
            print(f"DEBUG: Similarity neighbors found: {len(similarity_result.get('neighbors', [])) if similarity_result else 0}", flush=True)
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
        debug_info['credibility_status'] = resp.status_code
        try:
            debug_info['credibility_text'] = resp.text
        except Exception:
            debug_info['credibility_text'] = '<unreadable body>'
        print(f"DEBUG: Credibility response status: {resp.status_code}", flush=True)
        sys.stdout.flush()
        if resp.status_code == 200:
            credibility_result = resp.json()
            print(f"DEBUG: Credibility raw response: {credibility_result}", flush=True)
            sys.stdout.flush()
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
        if similarity_result and similarity_result.get('neighbors'):
            neighbors = similarity_result['neighbors']
            # Find the match with the highest similarity
            best_match = max(neighbors, key=lambda x: x['similarity']) if neighbors else None
            
            if best_match:
                s_conf = float(best_match['similarity'])
                s_verdict = str(best_match.get('verdict', '')).lower()
                
                # If we found an actual news article or a verified TRUE source, it is REAL
                is_s_fake = any(x in s_verdict for x in ['fake', 'false', 'අසත්‍ය'])
                
                # Boost weight for similarity matches. 
                # Even lower similarity from online search is a valid signal.
                if s_conf > 0.8:
                    s_weight = 2.0
                elif s_conf > 0.4:
                    s_weight = 1.5
                else:
                    s_weight = 1.0
                    
                signals.append({'is_fake': is_s_fake, 'conf': s_conf, 'weight': s_weight, 'source': 'similarity_max'})

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
            total_weight = sum(s['weight'] for s in signals)
            fake_score = sum(s['conf'] * s['weight'] for s in signals if s['is_fake'])
            real_score = sum(s['conf'] * s['weight'] for s in signals if not s['is_fake'])
            
            print(f"DEBUG: ENSEMBLE SUMMARY - Fake: {fake_score}, Real: {real_score}, Total Weight: {total_weight}", flush=True)

            if fake_score > real_score:
                final_prediction = "Fake"
                final_confidence = fake_score / total_weight
            elif real_score > fake_score:
                final_prediction = "Real"
                final_confidence = real_score / total_weight
            else:
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
    if debug_mode:
        result['_debug'] = debug_info

    return jsonify(result), 200


if __name__ == "__main__":
    # Allow overriding service URLs via environment (use container hostnames in compose)
    TAMIL_CLASSIFIER_URL = os.getenv("TAMIL_CLASSIFIER_URL", "http://127.0.0.1:1000")
    SINHALA_CLASSIFIER_URL = os.getenv("SINHALA_CLASSIFIER_URL", "http://127.0.0.1:2000")
    SIMILARITY_MATCHER_URL = os.getenv("SIMILARITY_MATCHER_URL", "http://127.0.0.1:3000")
    CREDIBILITY_PREDICTOR_URL = os.getenv("CREDIBILITY_PREDICTOR_URL", "http://127.0.0.1:4000")

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
