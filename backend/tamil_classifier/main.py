import uvicorn
import re
import io
import os
import shutil
import requests
import torch
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
from indicnlp import common
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from contextlib import asynccontextmanager
from PIL import Image
import cv2

# --- CONFIGURATION ---
PORT = 1000
MODEL_PATH = "./my_tamil_fake_news_model"
INDIC_RESOURCES_PATH = "./indic_nlp_resources"
OCR_MODEL_DIR = "./ocr_models"

# --- GLOBAL VARIABLES ---
classifier = None
normalizer = None
ocr_reader = None

# --- LOAD RESOURCES ---
def load_model_and_resources():
    global classifier, normalizer, ocr_reader
    
    print("--- SYSTEM STARTUP ---")

    # 1. NLP Resources
    print("1. Loading Indic NLP Resources...")
    try:
        common.set_resources_path(INDIC_RESOURCES_PATH)
        factory = IndicNormalizerFactory()
        normalizer = factory.get_normalizer("ta")
    except Exception as e:
        print(f"   Warning: Indic NLP not found ({e}). Normalization disabled.")

    # 2. Classification Model
    print(f"2. Loading Model from {MODEL_PATH}...")
    try:
        device = 0 if torch.cuda.is_available() else -1
        classifier = pipeline(
            "text-classification",
            model=MODEL_PATH,
            tokenizer=MODEL_PATH,
            device=device
        )
        print("   Fake News Model Loaded Successfully.")
    except Exception as e:
        print(f"   CRITICAL ERROR: Could not load model. {e}")

    # 3. Initialize EasyOCR (PRIMARY METHOD)
    print("3. Initializing EasyOCR...")
    try:
        import easyocr
        if not os.path.exists(OCR_MODEL_DIR):
            os.makedirs(OCR_MODEL_DIR)
        
        # Try with existing models first
        try:
            print("   Trying with existing models (download_enabled=False)...")
            ocr_reader = easyocr.Reader(
                ['ta', 'en'], 
                gpu=False,  # Force CPU to avoid GPU issues
                model_storage_directory=OCR_MODEL_DIR,
                download_enabled=False  # Don't download, use existing
            )
            print("   EasyOCR Initialized Successfully with existing models.")
        except Exception as e1:
            print(f"   Failed with existing models ({e1}), trying with download...")
            # If existing models don't work, try downloading
            try:
                ocr_reader = easyocr.Reader(
                    ['ta', 'en'], 
                    gpu=False,
                    model_storage_directory=OCR_MODEL_DIR,
                    download_enabled=True
                )
                print("   EasyOCR Initialized Successfully with downloaded models.")
            except Exception as e2:
                print(f"   Failed with download too ({e2})")
                ocr_reader = None
    except ImportError as ie:
        print(f"   CRITICAL: 'easyocr' library not found. Please run: pip install easyocr ({ie})")
        ocr_reader = None
    except Exception as e:
        print(f"   EasyOCR Init Failed: {e}")
        import traceback
        traceback.print_exc()
        ocr_reader = None

    print("--- STARTUP COMPLETE ---")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model_and_resources()
    yield

# --- APP SETUP ---
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
    """
    Cleans text by removing URLs and keeping only Tamil characters.
    """
    if not isinstance(text, str): text = str(text)
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    # Keep Tamil Unicode range (\u0B80-\u0BFF), spaces, and punctuation
    text = re.sub(r'[^\u0B80-\u0BFF\s.,!?]', ' ', text)
    
    if normalizer:
        return normalizer.normalize(text.strip()) if text.strip() else ""
    return text.strip()

def preprocess_image(image):
    """
    Preprocess image for better OCR results.
    """
    import cv2
    import numpy as np
    
    # Convert PIL to OpenCV format
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to get better contrast
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to PIL Image
    from PIL import Image
    processed_image = Image.fromarray(thresh)
    
    return processed_image

def perform_ocr(image):
    """
    Extracts text using EasyOCR with fallback options.
    """
    if not ocr_reader:
        print("Error: OCR Reader is not initialized.")
        return ""

    try:
        # Try original image first
        image_np = np.array(image)
        print(f"Original image shape: {image_np.shape}, dtype: {image_np.dtype}")

        results = ocr_reader.readtext(image_np, detail=0, paragraph=True)
        text = " ".join(results)
        
        print(f"OCR on original image extracted: '{text[:100]}...' (length: {len(text)})")
        
        # If no text found, try preprocessed image
        if not text.strip():
            print("No text found on original, trying preprocessed image...")
            processed_image = preprocess_image(image)
            image_np = np.array(processed_image)
            
            results = ocr_reader.readtext(image_np, detail=0, paragraph=True)
            text = " ".join(results)
            print(f"OCR on processed image extracted: '{text[:100]}...' (length: {len(text)})")
        
        # If still no text, try without paragraph mode
        if not text.strip():
            print("No text found with paragraph=True, trying without paragraph mode...")
            results = ocr_reader.readtext(image_np, detail=0, paragraph=False)
            text = " ".join(results)
            print(f"OCR without paragraph extracted: '{text[:100]}...' (length: {len(text)})")
        
        return text

    except Exception as e:
        print(f"EasyOCR Error: {e}")
        return ""

def predict_from_text(text: str):
    """
    Common logic for both text input and OCR input.
    """
    # 1. Clean the text
    cleaned = clean_text(text)
    
    # 2. Validation: Ensure we actually have Tamil text after cleaning
    if not cleaned or not re.search(r'[\u0B80-\u0BFF]', cleaned):
         return {
            "status": "error",
            "message": "Could not extract valid Tamil text from image. Try cropping the image to just the text.",
            "original_extracted": text
         }
         
    # 3. Predict
    try:
        result = classifier(cleaned)[0]
        is_fake = (result['label'] == 'LABEL_1') 
        
        return {
            "status": "success",
            "original_text": text,
            "cleaned_text": cleaned,
            "prediction": "Fake" if is_fake else "Real",
            "confidence": round(result['score'], 4)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Prediction failed: {str(e)}"
        }

# --- ENDPOINTS ---

@app.post("/predict")
async def predict_news(item: dict):
    return predict_from_text(item.get("text", ""))

@app.post("/predict_image_upload")
async def predict_image_upload(file: UploadFile = File(...)):
    try:
        print(f"Processing Upload: {file.filename}")
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert('RGB')
        
        extracted_text = perform_ocr(image)
        
        if not extracted_text.strip():
            return {
                "status": "error",
                "message": "No text found. If the image has complex backgrounds, try cropping it.",
                "original_extracted": ""
            }
            
        return predict_from_text(extracted_text)
        
    except Exception as e:
        print(f"Image Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict_image_url")
async def predict_image_url(item: dict):
    try:
        resp = requests.get(item['url'], timeout=10)
        image = Image.open(io.BytesIO(resp.content)).convert('RGB')
        
        extracted_text = perform_ocr(image)
        
        if not extracted_text.strip():
             return {
                "status": "error",
                "message": "No text found.",
                "original_extracted": ""
            }
             
        return predict_from_text(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)