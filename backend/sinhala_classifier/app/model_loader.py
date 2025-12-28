import joblib
import numpy as np

model = joblib.load("model/random_forest_model.pkl")
vectorizer = joblib.load("model/tfidf_vectorizer.pkl")

def predict_news(text: str):
    X = vectorizer.transform([text])
    prediction = model.predict(X)[0]
    probability = model.predict_proba(X)[0].max()

    label = "FAKE" if prediction == 1 else "REAL"

    return label, float(probability)
