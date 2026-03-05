import joblib
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- 1. Setup Flask App ---
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
PORT = 4000

# --- 2. Load Model & Encoder ---
try:
    # Ensure these files are in the same directory
    model = joblib.load('credibility_rf_model.pkl')
    encoder = joblib.load('lang_encoder.pkl')
    print("✅ Model and Encoder loaded successfully.")
except FileNotFoundError:
    print("❌ Error: Model files not found. Make sure .pkl files are present.")
    exit(1)

# --- 3. Prediction Logic ---
def get_prediction(data):
    # Create DataFrame from input dictionary
    df = pd.DataFrame([data])
    
    # Encode 'language' (using the loaded encoder)
    try:
        df['language'] = encoder.transform(df['language'])
    except Exception as e:
        return None, f"Error encoding language: {str(e)}"

    # Get Class Probabilities
    # model.classes_ usually gives ['High', 'Low', 'Medium'] (alphabetical)
    probs = model.predict_proba(df)[0]
    classes = model.classes_
    
    # Calculate Score (High=100, Medium=50, Low=0)
    score = 0
    confidence_breakdown = {}
    
    for class_name, prob in zip(classes, probs):
        confidence_breakdown[class_name] = round(prob * 100, 2)
        if class_name == 'High':
            score += prob * 100
        elif class_name == 'Medium':
            score += prob * 50
    
    # Get Final Label
    prediction_label = model.predict(df)[0]
    
    return {
        "credibility_score": round(score, 2),
        "prediction_label": prediction_label,
        "confidence_breakdown": confidence_breakdown
    }, None

# --- 4. Define API Endpoint ---
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Check for required fields
        required_fields = ['past_fake', 'past_real', 'domain_age_years', 'followers', 'language']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Missing fields. Required: {required_fields}"}), 400
            
        # Run Prediction
        result, error = get_prediction(data)
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 5. Run Server ---
if __name__ == '__main__':
    print(f"🚀 Backend running on http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, use_reloader=False)
