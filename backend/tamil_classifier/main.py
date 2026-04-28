import uvicorn
import re
import io
import os
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
import pytesseract

# If you are on WINDOWS, you must set this line to your installation path:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- CONFIGURATION ---
PORT = 1000
MODEL_PATH = "./my_tamil_fake_news_model"
INDIC_RESOURCES_PATH = "./indic_nlp_resources"

# --- GLOBAL VARIABLES ---
classifier = None
normalizer = None

# --- LOAD RESOURCES ---
def load_model_and_resources():
    global classifier, normalizer
    
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

    # 3. Tesseract OCR
    print("3. Tesseract OCR is ready (no pre-loading needed).")
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model_and_resources()
    yield
    print("--- SYSTEM SHUTDOWN ---")

# --- APP SETUP ---
app = FastAPI(title="Tamil Fake News Detector", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "message": "Tamil classifier service is running"}

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

def preprocess_for_tesseract(image: Image.Image):
    """
    Cleans the image for better Tesseract OCR results.
    """
    print("--- OCR: Preprocessing for Tesseract ---")
    # Convert PIL image to OpenCV format
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Resizing (Tesseract often works well with images around 300 DPI)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # 3. Denoising
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 4. Thresholding
    thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    return thresh

def perform_ocr(image: Image.Image):
    """
    Extracts text using Tesseract OCR.
    """
    try:
        processed_img = preprocess_for_tesseract(image)
        
        print("--- OCR: Extracting Text with Tesseract ---")
        # lang='tam+eng' tells it to look for both Tamil and English
        custom_config = r'-l tam+eng --psm 3'
        
        text = pytesseract.image_to_string(processed_img, config=custom_config)
        
        # Post-processing: Basic cleanup
        clean_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        
        print(f"--- OCR: Extracted Text ---\n{clean_text[:150]}...")
        return clean_text
    except pytesseract.TesseractNotFoundError:
        error_msg = "Tesseract is not installed or not in your PATH. Please install it."
        print(f"CRITICAL: {error_msg}")
        # Return a specific error message that the frontend can display
        return f"OCR_ERROR: {error_msg}"
    except Exception as e:
        print(f"An error occurred during Tesseract OCR: {e}")
        return ""

def predict_from_text(text: str):
    """
    Common logic for both text input and OCR input.
    """
    # Handle OCR-specific errors first
    if text.startswith("OCR_ERROR:"):
        return {"status": "error", "message": text.replace("OCR_ERROR: ", "")}

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