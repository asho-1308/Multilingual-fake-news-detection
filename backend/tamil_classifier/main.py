import uvicorn
import re
import io
import os
import requests
import torch
import numpy as np
import time
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
from transformers_interpret import SequenceClassificationExplainer
from indicnlp import common
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from contextlib import asynccontextmanager
from PIL import Image
import cv2
import pytesseract

import platform

# --- CONFIGURATION ---
PORT = 1000
MODEL_PATH = "./my_tamil_fake_news_model"
MODEL_VERSION = "1.0.0" 
INDIC_RESOURCES_PATH = "./indic_nlp_resources"

# Set Tesseract path based on OS
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- GLOBAL VARIABLES ---
classifier = None
normalizer = None
explainer = None 

# --- LOAD RESOURCES ---
def load_model_and_resources():
    global classifier, normalizer, explainer
    
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
        
        # 3. Initialize Model Explainer
        print("3. Initializing Model Explainer...")
        explainer = SequenceClassificationExplainer(classifier.model, classifier.tokenizer)
        print("   Explainer Initialized Successfully.")
        
    except Exception as e:
        print(f"   CRITICAL ERROR: Could not load model or explainer. {e}")

    # 4. Tesseract OCR
    print("4. Tesseract OCR is ready.")
    
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
def merge_tamil_subwords(attributions):
    """
    Groups BERT-style subwords (##) into full Tamil words for better readability.
    """
    merged = []
    for word, score in attributions:
        if word.startswith("##") and merged:
            prev_word, prev_score = merged[-1]
            merged[-1] = (prev_word + word[2:], prev_score + score)
        else:
            merged.append((word, score))
    return merged

def analyze_linguistic_markers(text: str):
    """
    Detects sensationalism, clickbait, and emotional hyperbole in Tamil news.
    """
    markers = {
        "sensationalism": [r"பகீர்", r"பரபரப்பு", r"அதிர்ச்சி", r"நிஜமா", r"உண்மை இதுவே"],
        "call_to_action": [r"பகிருங்கள்", r"ஷேர் செய்யுங்கள்", r"உடனே பாருங்கள்"],
        "honorific_misuse": [r"மதிப்பிற்குரிய", r"மாண்புமிகு"]
    }
    
    found = []
    score = 0
    for category, regex_list in markers.items():
        for regex in regex_list:
            if re.search(regex, text):
                found.append(regex.replace(r"", "")) # Simple display name
                score += 1
                
    intensity = "Low"
    if score >= 3: intensity = "High"
    elif score >= 1: intensity = "Medium"
    
    return {
        "intensity": intensity,
        "markers_found": list(set(found)),
        "sensationalism_score": score
    }

def clean_text(text: str):
    if not isinstance(text, str): text = str(text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'[^\u0B80-\u0BFF\s.,!?]', ' ', text)
    if normalizer:
        return normalizer.normalize(text.strip()) if text.strip() else ""
    return text.strip()

def preprocess_for_tesseract(image: Image.Image):
    print("--- OCR: Preprocessing for Tesseract ---")
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return thresh

def perform_ocr(image: Image.Image):
    try:
        processed_img = preprocess_for_tesseract(image)
        print("--- OCR: Extracting Text with Tesseract (Data Mode) ---")
        
        # Use image_to_data to get bounding boxes and confidence
        # This helps us identify the "headline" by looking at the height of text blocks
        data = pytesseract.image_to_data(processed_img, lang='tam+eng', output_type=pytesseract.Output.DICT)
        
        n_boxes = len(data['text'])
        blocks = {} # block_num -> list of words
        block_heights = {} # block_num -> avg height
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text: continue
            
            # Check if it contains Tamil
            if not re.search(r'[\u0B80-\u0BFF]', text): continue
            
            block_num = data['block_num'][i]
            height = data['height'][i]
            
            if block_num not in blocks:
                blocks[block_num] = []
                block_heights[block_num] = []
            
            blocks[block_num].append(text)
            block_heights[block_num].append(height)
            
        if not blocks:
            # Fallback to standard string if data mode fails to find Tamil
            custom_config = r'-l tam+eng --psm 3'
            text = pytesseract.image_to_string(processed_img, config=custom_config)
            lines = [l.strip() for l in text.splitlines() if l.strip() and re.search(r'[\u0B80-\u0BFF]', l)]
            return lines[0] if lines else ""

        # Identify the headline block: Usually the one with the largest average height 
        # (font size) or the first major block at the top.
        best_block = -1
        max_height_score = 0
        
        # EXCLUSION LIST: Words that indicate ads or sidebar data in certain layouts
        # Tesseract sometimes sees vertical text like "விளம்பரம்" (Advertisement) as "large" because it's stretched.
        exclusion_keywords = ["விளம்பரம்", "Share", "Follow"]

        for b_num in blocks:
            full_text = " ".join(blocks[b_num])
            
            # Skip if it's likely just an advertisement label
            if any(key in full_text for key in exclusion_keywords):
                print(f"--- OCR: Skipping block {b_num} (Exclusion keyword found) ---")
                continue

            avg_height = sum(block_heights[b_num]) / len(block_heights[b_num])
            
            # Headlines are usually near the top (lower block_num) and have largest font.
            # We use a score that heavily favors height but drops off for blocks deep in the image.
            # Block numbers usually increase as Tesseract scans down.
            position_bias = 2.0 if b_num <= 3 else (1.5 if b_num <= 6 else 1.0)
            
            # Additional check: headlines are usually long. Tiny blocks (1-2 short words) 
            # might be UI elements like 'Report' or 'Society'.
            length_bonus = 1.2 if len(full_text) > 15 else 1.0
            
            score = avg_height * position_bias * length_bonus
            
            # Detect if this block is exceptionally large (classic headline).
            # If we find a second large block right after first one, we merge them
            # to avoid truncation like "நடக்க உள்ள" vs "நடக்க உள்ள கூட்டங்கள்".
            if best_block != -1:
                # If this block is reasonably large and adjacent to the best block
                if avg_height > 15 and abs(b_num - best_block) <= 2:
                    print(f"--- OCR: Merging block {b_num} into {best_block} to prevent truncation ---")
                    blocks[best_block].extend(blocks[b_num])
                    continue

            print(f"--- OCR: Block {b_num} | Text: {full_text[:30]}... | Score: {score:.2f} (H: {avg_height:.1f})")

            if score > max_height_score:
                max_height_score = score
                best_block = b_num
                
        if best_block != -1:
            headline = " ".join(blocks[best_block])
            # Final Cleanup: Remove common UI suffixes if they somehow got attached
            headline = re.sub(r'in சமூகம்|in அரசியல்.*', '', headline).strip()
            print(f"--- OCR: Selected Headline ---\n{headline}")
            return headline
            
        return ""

    except pytesseract.TesseractNotFoundError:
        error_msg = "Tesseract is not installed or not in your PATH."
        print(f"CRITICAL: {error_msg}")
        return f"OCR_ERROR: {error_msg}"
    except Exception as e:
        print(f"An error occurred during Tesseract OCR: {e}")
        return ""

def predict_from_text(text: str):
    start_time = time.time()
    if text.startswith("OCR_ERROR:"):
        return {"status": "error", "message": text.replace("OCR_ERROR: ", "")}

    # If the input text has multiple lines (e.g. from a past OCR or manual paste), 
    # we focus on the first line as the 'headline' if it's significant.
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    main_text = lines[0] if lines else text

    cleaned = clean_text(main_text)
    if not cleaned or not re.search(r'[\u0B80-\u0BFF]', cleaned):
         return {
            "status": "error",
            "message": "Could not extract valid Tamil text. Try a clearer image or manually entering the headline.",
            "original_extracted": text
         }
         
    try:
        result = classifier(cleaned)[0]
        is_fake = (result['label'] == 'LABEL_1')
        prediction_label = "Fake" if is_fake else "Real"
        confidence = round(result['score'], 4)

        # 4. Explain Prediction
        trigger_words = []
        if explainer:
            try:
                raw_attributions = explainer(cleaned)
                # Filter out [CLS], [SEP] etc then merge
                filtered = [(w, s) for w, s in raw_attributions if not w.startswith("[")]
                merged_attributions = merge_tamil_subwords(filtered)
                
                trigger_words = [
                    {"word": word, "contribution": round(score, 4)}
                    for word, score in merged_attributions if score > 0
                ]
                trigger_words = sorted(trigger_words, key=lambda x: x['contribution'], reverse=True)[:5]
            except Exception as e:
                print(f"Could not generate explanation: {e}")

        # 5. Linguistic Analysis
        linguistic_report = analyze_linguistic_markers(cleaned)

        # 6. Interpret Confidence and Recommendation
        if confidence >= 0.9:
            confidence_level = "High"
            action_recommendation = "Reliable content pattern detected." if not is_fake else "Highly suspicious content detected."
        elif confidence >= 0.7:
            confidence_level = "Medium"
            action_recommendation = "Moderate risk. Cross-verification recommended."
        else:
            confidence_level = "Low"
            action_recommendation = "Inconclusive. Manual fact-check required."

        processing_time_ms = round((time.time() - start_time) * 1000)

        return {
            "status": "success",
            "prediction": prediction_label,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "recommendation": action_recommendation,
            "linguistic_analysis": linguistic_report,
            "original_text": text,
            "cleaned_text": cleaned,
            "explanation": {
                "summary": f"The model derived this {prediction_label} result from the following linguistic patterns.",
                "trigger_words": trigger_words
            },
            "metadata": {
                "language_detected": "ta",
                "processing_time_ms": processing_time_ms,
                "model_version": MODEL_VERSION,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Prediction failed: {str(e)}"
        }

@app.post("/predict")
async def predict_news(item: dict):
    return predict_from_text(item.get("text", ""))

@app.post("/predict_image_upload")
async def predict_image_upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert('RGB')
        extracted_text = perform_ocr(image)
        if not extracted_text.strip():
            return {"status": "error", "message": "No text found."}
        return predict_from_text(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict_image_url")
async def predict_image_url(item: dict):
    try:
        resp = requests.get(item['url'], timeout=10)
        image = Image.open(io.BytesIO(resp.content)).convert('RGB')
        extracted_text = perform_ocr(image)
        if not extracted_text.strip():
             return {"status": "error", "message": "No text found."}
        return predict_from_text(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
