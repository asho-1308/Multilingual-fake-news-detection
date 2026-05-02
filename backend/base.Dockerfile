FROM python:3.10-slim

# Install system dependencies common to all services
RUN apt-get update && apt-get install -y \
    git \
    curl \
    tesseract-ocr \
    tesseract-ocr-tam \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install common Python dependencies
RUN pip install --no-cache-dir --timeout=600 \
    torch==2.1.0 \
    transformers==4.36.0 \
    numpy==1.26.4 \
    scikit-learn==1.6.1 \
    pandas==2.0.3 \
    sentence-transformers==5.1.0 \
    huggingface-hub==0.19.4 \
    faiss-cpu==1.7.4 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    python-dotenv==1.0.0 \
    pydantic==2.5.0 \
    easyocr==1.7.1 \
    Pillow==10.1.0 \
    requests==2.31.0 \
    python-multipart==0.0.6 \
    pytesseract==0.3.10 \
    indic-nlp-library==0.92 \
    langdetect==1.0.9 \
    transformers-interpret==0.2.0

# Set working directory
WORKDIR /app