import uvicorn
import re
import io
import os
import shutil
import requests
import torch
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from transformers import pipeline
from indicnlp import common
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from contextlib import asynccontextmanager
from typing import List
from PIL import Image

# --- CONFIGURATION ---
PORT = 1000
MODEL_PATH = "./my_tamil_fake_news_model"
INDIC_RESOURCES_PATH = "./indic_nlp_resources"
OCR_MODEL_DIR = "./ocr_models"

# Tesseract Configuration (Windows Path)
# If you don't have Tesseract installed, download it from: https://github.com/UB-Mannheim/tesseract/wiki
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- GLOBAL VARIABLES ---
classifier = None
normalizer = None
ocr_reader = None
use_tesseract = False

# --- NUCLEAR CACHE CLEANER ---
def clean_corrupted_easyocr_cache():
    """Deletes EasyOCR cache from both local and user directories."""
    paths_to_clean = [
        OCR_MODEL_DIR,
        os.path.join(os.path.expanduser("~"), ".EasyOCR") # Checks C:\Users\LENOVO\.EasyOCR
    ]
    
    print("--- CHECKING FOR CORRUPTED OCR MODELS ---")
    for path in paths_to_clean:
        if os.path.exists(path):
            try:
                print(f"Deleting cached models in: {path}")
                shutil.rmtree(path)
                print("Deleted successfully.")
            except Exception as e:
                print(f"Warning: Could not delete {path}. Reason: {e}")
    print("-------------------------------------------")

# --- LOAD RESOURCES ---
def load_model_and_resources():
    global classifier, normalizer, ocr_reader, use_tesseract
    
    # 1. Clean Cache to prevent "size mismatch" errors
    clean_corrupted_easyocr_cache()

    # 2. Load NLP Resources
    print("Loading Indic NLP Resources...")
    try:
        common.set_resources_path(INDIC_RESOURCES_PATH)
        factory = IndicNormalizerFactory()
        normalizer = factory.get_normalizer("ta")
    except Exception:
        print("Warning: Indic NLP not found. Normalization disabled.")

    # 3. Load Classification Model
    print(f"Loading Model from {MODEL_PATH}...")
    try:
        device = -1 # Force CPU to avoid CUDA warnings if unstable
        if torch.cuda.is_available():
            device = 0
            
        classifier = pipeline(
            "text-classification",
            model=MODEL_PATH,
            tokenizer=MODEL_PATH,
            device=device
        )
        print("Fake News Model Loaded Successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not load model. {e}")
        raise e

    # 4. Initialize EasyOCR (with Tesseract Fallback)
    print("Initializing EasyOCR...")
    try:
        import easyocr
        # Force fresh download to local folder
        if not os.path.exists(OCR_MODEL_DIR):
            os.makedirs(OCR_MODEL_DIR)
            
        ocr_reader = easyocr.Reader(
            ['ta', 'en'], 
            gpu=torch.cuda.is_available(),
            model_storage_directory=OCR_MODEL_DIR,
            download_enabled=True
        )
        print("EasyOCR Initialized Successfully.")
    except Exception as e:
        print(f"EasyOCR Failed to Init: {e}")
        print("Switching to Tesseract Fallback...")
        ocr_reader = None

    # 5. Initialize Tesseract
    try:
        import pytesseract
        if os.path.exists(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            use_tesseract = True
            print(f"Tesseract configured at: {TESSERACT_PATH}")
        else:
            print("Tesseract executable not found. Image analysis might fail if EasyOCR also fails.")
    except ImportError:
        print("pytesseract library not installed. Run 'pip install pytesseract'")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model_and_resources()
    yield

# --- APP SETUP ---
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Tamil Fake News Detector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOGIC ---
def clean_text(text: str):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'[^\u0B80-\u0BFF\s.,!?]', '', text)
    if normalizer:
        return normalizer.normalize(text.strip()) if text.strip() else ""
    return text.strip()

def perform_ocr(image):
    """Robust OCR that tries EasyOCR first, then Tesseract."""
    text = ""
    
    # Try EasyOCR
    if ocr_reader:
        try:
            results = ocr_reader.readtext(np.array(image))
            text = " ".join([res[1] for res in results])
        except Exception as e:
            print(f"EasyOCR Runtime Error: {e}")
    
    # If EasyOCR failed or returned nothing, try Tesseract
    if not text.strip() and use_tesseract:
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, lang='tam+eng')
        except Exception as e:
            print(f"Tesseract Runtime Error: {e}")
            
    return text

def predict_from_text(text: str):
    cleaned = clean_text(text)
    if not cleaned or not re.search(r'[\u0B80-\u0BFF]', cleaned):
         raise HTTPException(status_code=400, detail="Could not extract valid Tamil text from image.")
         
    result = classifier(cleaned)[0]
    is_fake = (result['label'] == 'LABEL_1')
    return {
        "original_text": text,
        "prediction": "Fake" if is_fake else "Real",
        "confidence": round(result['score'], 4),
        "cleaned_text": cleaned
    }

# --- ENDPOINTS ---
@app.post("/predict")
async def predict_news(item: dict):
    return predict_from_text(item.get("text", ""))

@app.post("/predict_bulk")
async def predict_bulk(item: dict):
    texts = item.get("texts", [])
    results = []
    for t in texts:
        try:
            results.append(predict_from_text(t))
        except:
            continue
    return results

@app.post("/predict_image_upload")
async def predict_image_upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert('RGB')
        
        extracted_text = perform_ocr(image)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text found in image. Try a clearer image.")
            
        return predict_from_text(extracted_text)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # Print the ACTUAL error to console
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.post("/predict_image_url")
async def predict_image_url(item: dict):
    try:
        resp = requests.get(item['url'], timeout=10)
        image = Image.open(io.BytesIO(resp.content)).convert('RGB')
        
        extracted_text = perform_ocr(image)
        
        if not extracted_text.strip():
             raise HTTPException(status_code=400, detail="No text found in image.")
             
        return predict_from_text(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)