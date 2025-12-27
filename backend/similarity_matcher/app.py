from flask import Flask, request, jsonify
from flask_cors import CORS

from semantic_model import SemanticVerifierService  # if file is semantic_model.py
from config import HOST, PORT, DEBUG, TOP_K


app = Flask(__name__)
CORS(app)  # allow requests from your React frontend, Postman, etc.

# Load model + FAISS + dataset once at startup
service = SemanticVerifierService()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Semantic verifier service is running"}), 200


@app.route("/api/verify", methods=["POST"])
def verify():
    """
    Expected JSON body:
    {
      "claim": "text of the claim",
      "top_k": 3   # optional
    }
    """
    try:
        data = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    if not data or "claim" not in data:
        return jsonify({"error": "Missing 'claim' in request body"}), 400

    claim = str(data["claim"]).strip()
    if not claim:
        return jsonify({"error": "Claim cannot be empty"}), 400

    top_k = data.get("top_k", TOP_K)
    try:
        top_k = int(top_k)
        if top_k <= 0:
            top_k = TOP_K
    except Exception:
        top_k = TOP_K

    try:
        result = service.verify_claim(claim, top_k=top_k)
        return jsonify(result), 200
    except Exception as e:
        # For debugging you can print(e), but avoid leaking internals in prod
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    print(f"🚀 Starting Semantic Verifier API on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
