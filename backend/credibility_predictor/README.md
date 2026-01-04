# Credibility Predictor

A machine learning-based service for assessing the credibility of news sources. This component evaluates news source reliability using historical fake/real news counts, domain age, follower count, and language features.

## Overview

The Credibility Predictor uses a trained Random Forest classifier to predict whether a news source is High, Medium, or Low credibility. It processes input features and returns a credibility score along with confidence breakdowns.

## Features

- **Machine Learning Model**: Random Forest classifier trained on source credibility data
- **REST API**: Flask-based API for real-time predictions
- **Multi-language Support**: Handles different languages via label encoding
- **Credibility Scoring**: Provides numerical score (0-100) and categorical label

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation

1. Navigate to the credibility_predictor directory:
   ```bash
   cd backend/credibility_predictor
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Model Training

The model is trained using the Jupyter notebook `notebooks/credibility_Predictor/credibility_prediction.ipynb`.

### Requirements for Training

- Dataset: `source_credibility_dataset_200.csv` with columns:
  - `past_fake`: Number of past fake news articles
  - `past_real`: Number of past real news articles
  - `domain_age_years`: Age of the domain in years
  - `followers`: Number of followers/subscribers
  - `language`: Language code (e.g., 'en', 'si', 'ta')
  - `credibility_label`: Target label ('High', 'Medium', 'Low')

### Training Steps

1. Open the notebook in Jupyter
2. Ensure the dataset file is in the same directory
3. Run all cells to train the model and save `credibility_rf_model.pkl` and `lang_encoder.pkl`

## Running the Service

1. Ensure model files are present in the directory
2. Run the Flask app:
   ```bash
   python app.py
   ```

The service will start on `http://localhost:4000`

## API Documentation

### POST /predict

Predicts the credibility of a news source.

**Request Body:**
```json
{
  "past_fake": 10,
  "past_real": 20,
  "domain_age_years": 5,
  "followers": 1000,
  "language": "en"
}
```

**Response:**
```json
{
  "credibility_score": 75.0,
  "prediction_label": "High",
  "confidence_breakdown": {
    "High": 75.0,
    "Medium": 20.0,
    "Low": 5.0
  }
}
```

**Error Response:**
```json
{
  "error": "Error message"
}
```

### Input Fields

- `past_fake` (int): Number of fake news articles published by the source
- `past_real` (int): Number of real news articles published by the source
- `domain_age_years` (float): Age of the domain in years
- `followers` (int): Number of followers or subscribers
- `language` (str): Language code (must match training data)

### Output Fields

- `credibility_score` (float): Score from 0-100 (High=100, Medium=50, Low=0)
- `prediction_label` (str): Predicted credibility level
- `confidence_breakdown` (dict): Probabilities for each class

## Docker

To run with Docker:

```bash
docker build -t credibility-predictor .
docker run -p 4000:4000 credibility-predictor
```

## Health Check

The service includes a health check endpoint in Docker Compose configuration, but it's not implemented in the Flask app. For production, add:

```python
@app.route('/health')
def health():
    return {"status": "healthy"}
```

## Dependencies

- Flask==2.3.3
- flask-cors==4.0.0
- pandas
- scikit-learn
- joblib

## Model Details

- **Algorithm**: Random Forest Classifier
- **Features**: past_fake, past_real, domain_age_years, followers, language (encoded)
- **Classes**: High, Medium, Low
- **Evaluation**: Accuracy score and classification report available in training notebook

## Troubleshooting

- **Model files not found**: Ensure `credibility_rf_model.pkl` and `lang_encoder.pkl` are in the directory
- **Import errors**: Activate virtual environment and install requirements
- **Port conflicts**: Change PORT in app.py if 4000 is in use

## Contributing

1. Train new models using the notebook
2. Update requirements.txt for new dependencies
3. Test API endpoints
4. Update this README for changes
