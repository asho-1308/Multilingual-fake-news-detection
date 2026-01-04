# Tamil Fake News Classifier

A FastAPI-based service for detecting fake news in Tamil language content. This classifier supports text input, image uploads with OCR (Optical Character Recognition), and image URLs. It uses a fine-tuned transformer model trained on Tamil news data, Indic NLP for text normalization, and EasyOCR for extracting Tamil text from images.

## Features

- **Text Classification**: Direct prediction on Tamil text input
- **Image OCR**: Automatic text extraction from uploaded images or URLs
- **Tamil Language Support**: Specialized preprocessing for Tamil script (Unicode range \u0B80-\u0BFF)
- **Text Normalization**: Uses Indic NLP library for proper Tamil text normalization
- **Confidence Scores**: Provides prediction confidence along with binary classification
- **CORS Enabled**: Supports cross-origin requests for web integration
- **Docker Support**: Containerized deployment with health checks

## Architecture

The service consists of three main components:

1. **Text Preprocessing**: Cleans URLs, filters non-Tamil characters, and normalizes text
2. **Classification Model**: Fine-tuned transformer model for fake/real news detection
3. **OCR Engine**: EasyOCR for Tamil and English text extraction from images

## API Endpoints

### Base URL
```
http://localhost:1000
```

### 1. Text Prediction
**Endpoint**: `POST /predict`

**Request Body**:
```json
{
  "text": "உங்கள் தமிழ் செய்தி உரை இங்கே"
}
```

**Response**:
```json
{
  "status": "success",
  "original_text": "உங்கள் தமிழ் செய்தி உரை இங்கே",
  "cleaned_text": "normalized tamil text",
  "prediction": "Fake" | "Real",
  "confidence": 0.9876
}
```

### 2. Image Upload Prediction
**Endpoint**: `POST /predict_image_upload`

**Request**: Multipart form data with image file

**Response**: Same as text prediction, includes extracted text

### 3. Image URL Prediction
**Endpoint**: `POST /predict_image_url`

**Request Body**:
```json
{
  "url": "https://example.com/image.jpg"
}
```

**Response**: Same as text prediction

## Installation

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Local Setup

1. **Clone and navigate**:
   ```bash
   cd backend/tamil_classifier
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download OCR models** (optional, will download automatically on first run):
   ```bash
   # Models will be stored in ./ocr_models/
   ```

### Docker Setup

The service uses a common base image. Build and run with Docker Compose from the project root:

```bash
docker-compose up tamil-classifier
```

## Usage

### Starting the Service

```bash
python main.py
```

The service will start on `http://localhost:1000`

### Testing

Use the provided test script:

```bash
python test_api.py
```

This will test all endpoints with sample data.

### Example Usage

```python
import requests

# Text prediction
response = requests.post("http://localhost:1000/predict",
                        json={"text": "உங்கள் தமிழ் செய்தி"})
print(response.json())

# Image upload
with open("news_image.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:1000/predict_image_upload", files=files)
print(response.json())
```

## Model Details

- **Model Type**: Transformer-based text classification
- **Training Data**: Tamil news articles (fake vs real)
- **Preprocessing**: Indic NLP normalization, URL removal, script filtering
- **Labels**: `LABEL_0` (Real), `LABEL_1` (Fake)

## OCR Configuration

- **Engine**: EasyOCR
- **Languages**: Tamil (`ta`) and English (`en`)
- **Preprocessing**: Grayscale conversion, thresholding for better accuracy
- **Fallbacks**: Multiple OCR attempts with different settings

## Error Handling

The API returns structured error responses:

```json
{
  "status": "error",
  "message": "Error description",
  "original_extracted": "extracted text if applicable"
}
```

Common errors:
- No Tamil text found in image
- Model loading failures
- Invalid image formats
- Network timeouts for URL fetching

## Performance

- **Text Prediction**: ~100-500ms per request
- **OCR + Prediction**: ~5-15 seconds per image (depends on image complexity)
- **Memory Usage**: ~2-4GB RAM (with GPU acceleration if available)

## Dependencies

Key libraries:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `transformers`: Hugging Face models
- `torch`: PyTorch for model inference
- `indic-nlp-library`: Tamil text processing
- `easyocr`: OCR functionality
- `Pillow`: Image processing

## Configuration

Modify these constants in `main.py`:

```python
PORT = 1000
MODEL_PATH = "./my_tamil_fake_news_model"
INDIC_RESOURCES_PATH = "./indic_nlp_resources"
OCR_MODEL_DIR = "./ocr_models"
```

## Troubleshooting

### Common Issues

1. **OCR not working**: Ensure EasyOCR models are downloaded
2. **Model loading errors**: Check model files exist in `my_tamil_fake_news_model/`
3. **Indic NLP errors**: Verify `indic_nlp_resources/` directory
4. **Memory issues**: Use CPU mode or reduce batch size

### Logs

Check console output for detailed error messages and OCR extraction results.

## Integration

This service is part of the Multilingual Fake News Detection system. It integrates with:

- Frontend UI components
- Orchestrator service
- Other language classifiers (Sinhala, etc.)

For full system integration, refer to the main project README.

## License

[Add license information if applicable]

## Contributing

[Add contribution guidelines if applicable]
