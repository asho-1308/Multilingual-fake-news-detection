import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from semantic_model import SemanticVerifierService

app = Flask(__name__)
CORS(app)

# ✅ Load service once when app starts (Flask 3.x compatible)
service = SemanticVerifierService()

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Semantic verifier service is running"
    })

@app.post("/api/verify")
def api_verify():
    data = request.get_json(silent=True) or {}
    claim = str(data.get("claim", "")).strip()
    top_k = data.get("top_k", None)
    # Mode controls where to search: 'auto' (default), 'local', 'online', or 'both'
    mode = str(data.get("mode", "auto")).strip().lower()
    debug = bool(data.get("debug", False))

    if not claim:
        return jsonify({"error": "Missing 'claim' in request body"}), 400

    # validate top_k
    try:
        if top_k is not None:
            top_k = int(top_k)
            if top_k < 1 or top_k > 10:
                return jsonify({"error": "top_k must be between 1 and 10"}), 400
    except:
        return jsonify({"error": "top_k must be an integer"}), 400

    try:
        # validate mode
        if mode not in ("auto", "local", "online", "both"):
            return jsonify({"error": "mode must be one of: auto, local, online, both"}), 400

        result = service.verify(claim, top_k=top_k, mode=mode, debug=debug)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Verification failed", "details": str(e)}), 500


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3000"))
    print(f"🚀 Starting Semantic Verifier API on http://{host}:{port}")
    # Disable reloader on Windows to prevent WinError 10038 and unnecessary reloading
    app.run(host=host, port=port, debug=True, use_reloader=False)
