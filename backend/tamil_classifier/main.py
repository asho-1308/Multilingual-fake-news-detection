import uvicorn
import re
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
from indicnlp import common
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from contextlib import asynccontextmanager
from typing import List

# --- CONFIGURATION ---
PORT = 1000
MODEL_PATH = "./my_tamil_fake_news_model"  # Path to your downloaded model
INDIC_RESOURCES_PATH = "./indic_nlp_resources" # Path to the cloned repo

# --- GLOBAL VARIABLES FOR MODEL ---
classifier = None
normalizer = None

def load_model_and_resources():
    global classifier, normalizer
    
    print("Loading Indic NLP Resources...")
    try:
        common.set_resources_path(INDIC_RESOURCES_PATH)
        factory = IndicNormalizerFactory()
        normalizer = factory.get_normalizer("ta") # Tamil Normalizer
    except Exception as e:
        print(f"Error loading Indic NLP resources: {e}")
        print("Ensure you have cloned https://github.com/anoopkunchukuttan/indic_nlp_resources.git into the project folder.")
        raise e

    print(f"Loading Model from {MODEL_PATH}...")
    try:
        # Load Model and Tokenizer into a pipeline
        device = 0 if torch.cuda.is_available() else -1
        classifier = pipeline(
            "text-classification",
            model=MODEL_PATH,
            tokenizer=MODEL_PATH,
            device=device
        )
        if device == 0:
            print("Model loaded on GPU.")
        else:
            print("Model loaded on CPU.")
            
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Ensure you have downloaded the model folder from Google Drive.")
        raise e

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    load_model_and_resources()
    yield
    # Clean up the ML models and release the resources
    # (if needed)

from fastapi.middleware.cors import CORSMiddleware

# --- APP INITIALIZATION ---
app = FastAPI(title="Tamil Fake News Detector API", lifespan=lifespan)

# --- CORS MIDDLEWARE ---
# This allows the frontend (running on a different port) to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- PREPROCESSING HELPER (Must match Notebook exactly) ---
def clean_text(text: str):
    if not isinstance(text, str):
        text = str(text)
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    # Remove non-Tamil characters (keeping punctuation)
    text = re.sub(r'[^\u0B80-\u0BFF\s.,!?]', '', text)
    # Normalize
    return normalizer.normalize(text.strip()) if text.strip() else ""

# --- API DATA MODELS ---
class NewsRequest(BaseModel):
    text: str

class NewsListRequest(BaseModel):
    texts: List[str]

class PredictionResponse(BaseModel):
    original_text: str
    cleaned_text: str
    prediction: str
    confidence: float
    is_fake: bool

# --- API ENDPOINTS ---
@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_news(news: NewsRequest):
    if not classifier:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")

    try:
        # 1. Preprocess
        cleaned_text = clean_text(news.text)
        
        if not cleaned_text or not re.search(r'[\u0B80-\u0BFF]', cleaned_text):
            raise HTTPException(status_code=400, detail="Input text contains no valid Tamil characters after cleaning.")

        # 2. Predict using the pipeline
        result = classifier(cleaned_text)[0]
        
        # 3. Map Labels (Based on your notebook: LABEL_0 = Real, LABEL_1 = Fake)
        label = result['label']
        confidence = result['score']
        
        prediction_label = "Real" if label == 'LABEL_0' else "Fake"
        is_fake_bool = (label == 'LABEL_1')

        return PredictionResponse(
            original_text=news.text,
            cleaned_text=cleaned_text,
            prediction=prediction_label,
            confidence=round(confidence, 4),
            is_fake=is_fake_bool
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/predict_bulk", response_model=List[PredictionResponse], tags=["Prediction"])
async def predict_news_bulk(news_list: NewsListRequest):
    if not classifier:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")

    responses = []
    
    # Clean all texts first
    cleaned_texts = [clean_text(text) for text in news_list.texts]
    
    # Filter out empty texts to avoid sending them to the model
    valid_texts = [text for text in cleaned_texts if text and re.search(r'[\u0B80-\u0BFF]', text)]
    
    if not valid_texts:
        raise HTTPException(status_code=400, detail="None of the input texts contain valid Tamil characters after cleaning.")

    try:
        # Predict in a batch
        bulk_results = classifier(valid_texts)

        # Create a map of cleaned text to its original text
        original_text_map = {cleaned: original for original, cleaned in zip(news_list.texts, cleaned_texts) if cleaned in valid_texts}
        
        # Process results
        for i, result in enumerate(bulk_results):
            cleaned_text = valid_texts[i]
            original_text = original_text_map[cleaned_text]
            
            label = result['label']
            confidence = result['score']
            
            prediction_label = "Real" if label == 'LABEL_0' else "Fake"
            is_fake_bool = (label == 'LABEL_1')

            responses.append(PredictionResponse(
                original_text=original_text,
                cleaned_text=cleaned_text,
                prediction=prediction_label,
                confidence=round(confidence, 4),
                is_fake=is_fake_bool
            ))
            
        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during bulk prediction: {str(e)}")

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Run uvicorn server on port 1000
    uvicorn.run(app, host="0.0.0.0", port=PORT)