import joblib
import json
from dummy_model import DummyModel, DummyEncoder


def save(obj, path):
    joblib.dump(obj, path)
    print(f"Saved (joblib) {path}")


if __name__ == '__main__':
    model = DummyModel()
    encoder = DummyEncoder()

    save(model, 'credibility_rf_model.pkl')
    save(encoder, 'lang_encoder.pkl')

    # Emit a small sample JSON showing what the model would output for a sample row
    sample = {
        'past_fake': 3,
        'past_real': 3,
        'domain_age_years': 2,
        'followers': 3243442,
        'language': 'sinhala'
    }

    import pandas as pd
    df = pd.DataFrame([sample])
    df['language'] = encoder.transform(df['language'])
    probs = model.predict_proba(df)[0]
    classes = model.classes_
    credibility_score = 0
    for cls, p in zip(classes, probs):
        if cls == 'High':
            credibility_score += p * 100
        elif cls == 'Medium':
            credibility_score += p * 50
    result = {
        'credibility_score': round(credibility_score,2),
        'prediction_label': model.predict(df)[0],
        'confidence_breakdown': {c: round(p*100,2) for c,p in zip(classes,probs)}
    }
    print('Sample prediction:', json.dumps(result, ensure_ascii=False))
