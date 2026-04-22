# Multilingual Fake News Detection System

A comprehensive AI-powered system for detecting fake news in Tamil and Sinhala languages. The system combines multiple specialized components to provide accurate fake news detection through text analysis, source credibility assessment, and fact-checking against verified sources.

## 🏗️ Architecture Overview

The system consists of microservices architecture with the following components:

### Core Services (Main 4 Functions)

1. **📰 Tamil Classifier** (Port 1000)
   - **Function**: Detects fake news in Tamil language content
   - **Features**: Text classification, OCR for Tamil images, Indic NLP normalization
   - **Technology**: FastAPI, Transformers, EasyOCR, Indic NLP Library
   - **Model**: Fine-tuned transformer model trained on Tamil news dataset
   - **API Schema**: Returns `{status: "success", prediction: "Fake/Real", confidence: float}`

2. **📰 Sinhala Classifier** (Port 2000)
   - **Function**: Detects fake news in Sinhala language content
   - **Features**: Text classification with Sinhala language processing
   - **Technology**: FastAPI, Machine learning models
   - **Model**: ML model trained on Sinhala news data
   - **API Schema**: Returns `{label: "FAKE/REAL", confidence: float}`

3. **🔍 Similarity Matcher** (Port 3000)
   - **Function**: Fact-checks claims against verified news sources using semantic similarity
   - **Features**: Semantic search, multilingual support, FAISS indexing
   - **Technology**: FastAPI, Sentence Transformers, FAISS
   - **Data**: Pre-indexed verified sources in multiple languages

4. **⚖️ Credibility Predictor** (Port 4000)
   - **Function**: Assesses news source credibility based on historical data
   - **Features**: ML-based prediction using source features
   - **Technology**: Flask, Scikit-learn, Random Forest
   - **Inputs**: Past fake/real counts, domain age, follower count, language
   - **Config**: Disables Flask reloader (`use_reloader=False`) to ensure Windows compatibility with subprocesses.

### Supporting Services

5. **🎯 Orchestrator** (Port 5000)
   - **Function**: Main coordinator that routes requests based on language detection
   - **Features**: Automatic language detection, weighted ensemble analysis, result aggregation
   - **Networking**: Uses `127.0.0.1` for internal routing to avoid IPv6 `[::1]` resolution issues on Windows.
   - **Ensemble Logic**: Combines signals from classifiers, similarity matches, and source credibility using a weighted scoring system:
     - **Linguistic Classifier**: Expert signal (Weight: High)
     - **Similarity Matcher**: Direct fact-check signal (Weight: Critical if match found)
     - **Credibility Predictor**: Contextual supporting signal (Weight: Supporting)
   - **Technology**: Flask, LangDetect
   - **Windows Deployment**: Configured with `use_reloader=False` to prevent `WinError 10038` when spawning background microservices.

6. **🖥️ Frontend** (Port 8080)
   - **Function**: User interface for interacting with the detection system
   - **Features**: React-based UI, real-time predictions, multi-language support
   - **Backend Connection**: Configured to connect to `http://127.0.0.1:5000/predict` for optimized Windows performance.
   - **Technology**: React, Vite, TypeScript, Tailwind CSS

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Windows PowerShell (for the utility script)

### Run the Full Backend
Run all backend microservices with a single command (recommended). The project includes a PowerShell helper that builds the common base image and starts every service in detached mode.

Prerequisite (Windows): make sure **Docker Desktop** is running.

**Recommended (one command — Windows PowerShell)**
```powershell
cd C:\Users\LENOVO\Desktop\Multilingual-fake-news-detection
.\run-backend.ps1
```

**Direct Docker Compose (alternative)**
- Build the common base image (only required once or after dependency changes):
```powershell
docker build -t multilingual-fake-news-detection-base:latest -f ./backend/base.Dockerfile ./backend
```
- Start all services with Compose:
```powershell
docker compose up --build -d
```

Quick verification:
```powershell
docker compose ps
docker compose logs -f        # tail all logs
curl http://localhost:5000/health   # orchestrator health
```

---

### Individual Service Access
Once running, you can access the services at:
- **Main API (Orchestrator)**: [http://localhost:5000](http://localhost:5000)
- **Web Frontend**: [http://localhost:8080](http://localhost:8080)
- **Tamil Classifier**: [http://localhost:1000](http://localhost:1000)
- **Sinhala Classifier**: [http://localhost:2000](http://localhost:2000)
- **Similarity Matcher**: [http://localhost:3000](http://localhost:3000)
- **Credibility Predictor**: [http://localhost:4000](http://localhost:4000)
- 8GB+ RAM recommended
- Python 3.8+ (for local development)

### Docker Deployment (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd multilingual-fake-news-detection
   ```

2. **Recommended — start everything (Windows)**
   ```powershell
   # preferred: use helper which builds the base image and starts all services
   .\run-backend.ps1
   ```

   Or manually with Docker Compose v2:
   ```bash
   docker build -t multilingual-fake-news-detection-base:latest -f ./backend/base.Dockerfile ./backend
   docker compose up --build -d
   ```

3. **Check service health**:
   ```bash
   docker compose ps
   ```

4. **Access the application**:
   - Frontend: http://localhost:8080
   - API Documentation / Orchestrator: http://localhost:5000



   ### Chrome Extension (Updated UI)

   A modern, redesigned Chrome extension is included to scan news headings and show real-time verification results directly on the page.

   - **Features**: 
     - **Headlines Scanner**: Automatically detects Tamil and Sinhala headings on active news sites.
     - **Rich Overlays**: Displays color-coded results (**Green** for Real, **Red** for Fake) next to headings.
     - **Detailed Metrics**: Shows confidence percentage balance and specific match data from the backend.
     - **Ensemble Logic**: Uses an improved backend voting system to distinguish between "Real," "Fake," and "Unknown" content.

   Installation (developer mode)

   1. Ensure the orchestrator is running at `http://localhost:5000` (or update the extension code to point to a remote API).
   2. Open Chrome and go to `chrome://extensions`.
   3. Enable **Developer mode** (top-right).
   4. Click **Load unpacked** and select the `chrome-extension` folder in the repository.
   5. The extension icon will appear in the toolbar. Click it and press **Scan Headings**.

   Usage

   - Click **Scan Headings** to detect page headings. Detected headings are listed in the popup.
   - Click **Analyze** next to a heading to call the orchestrator and display a small overlay with the prediction and confidence.
   - If the content script cannot be injected (some pages or CSP restrictions), the popup will fall back to injecting a scanner function using `chrome.scripting.executeScript`.

   Developer notes

   - The extension uses `chrome.scripting.executeScript` as a fallback when content scripts are not present on the page.
   - The content script is `chrome-extension/content_script.js` and the popup UI is `chrome-extension/popup.html` + `popup.js`.
   - Icon files are under `chrome-extension/icons/` and the manifest is `chrome-extension/manifest.json`.
   - To test without the backend, you can temporarily modify `content_script.js` to mock responses or the popup to show simulated outputs.

   Security & privacy

   - The extension only scans headings (H1–H6 and common headline classes) when you click the popup; it does not automatically send page content without user action.
   - Be careful when using the extension on sites with sensitive content — you can choose to run the extension only on pages you trust.
   - For production deployment, host the backend on a secure HTTPS endpoint and update `host_permissions` in the manifest accordingly.


### Local Development Setup

1. **Backend Setup**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # Install dependencies for each service
   cd backend/tamil_classifier && pip install -r requirements.txt
   cd ../sinhala_classifier && pip install -r requirements.txt
   cd ../similarity_matcher && pip install -r requirements.txt
   cd ../credibility_predictor && pip install -r requirements.txt
   cd ../orchestrator && pip install -r requirements.txt
   ```

2. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Start Services**:
   ```bash
   # Start each service in separate terminals
   cd backend/tamil_classifier && python main.py
   cd backend/sinhala_classifier && python -m uvicorn app.main:app --host 0.0.0.0 --port 2000 --reload
   cd backend/similarity_matcher && python app.py
   cd backend/credibility_predictor && python app.py
   cd backend/orchestrator && python app.py
   ```

## 📡 API Usage

### Main Endpoint (Orchestrator)

**URL**: `POST http://localhost:5000/predict`

**Request**:
```json
{
  "text": "Your news text in Tamil or Sinhala"
}
```

**Response**:
```json
{
  "language": "tamil",
  "final_prediction": "Real",
  "final_confidence": 0.89,
  "classifier": {
    "prediction": "Real",
    "confidence": 0.89
  },
  "similarity": {
    "final_verdict": "Likely TRUE",
    "confidence": 0.95,
    "neighbors": [...]
  },
  "credibility": {
    "credibility": "High",
    "confidence": 0.85000
  }
}
```

### Individual Service Endpoints

#### Tamil Classifier
- **Text**: `POST http://localhost:1000/predict`
- **Image Upload**: `POST http://localhost:1000/predict_image_upload`
- **Image URL**: `POST http://localhost:1000/predict_image_url`

#### Sinhala Classifier
- **Text**: `POST http://localhost:2000/predict`

#### Similarity Matcher
- **Verify Claim**: `POST http://localhost:3000/api/verify`

#### Credibility Predictor
- **Predict**: `POST http://localhost:4000/predict`

## 🔧 Configuration

### Environment Variables

Each service can be configured via environment variables:

```bash
# Tamil Classifier
USE_CUDA=false
LOG_LEVEL=INFO

# General
FLASK_ENV=production
```

### Model Files

Ensure model files are in place:
- `backend/tamil_classifier/my_tamil_fake_news_model/`
- `backend/sinhala_classifier/model/`
- `backend/similarity_matcher/artifacts/`
- `backend/credibility_predictor/` (credibility_rf_model.pkl, lang_encoder.pkl)

## 🧪 Testing

### API Testing

Use the test scripts in each service directory:

```bash
# Tamil Classifier
cd backend/tamil_classifier && python test_api.py

# Sinhala Classifier
cd backend/sinhala_classifier && python test_api.py
```

### Health Checks

All services include health endpoints:
- `GET /health` on each service port

## 📊 Data Flow

1. **Input**: User submits text via frontend or API
2. **Language Detection**: Orchestrator detects language (Tamil/Sinhala/English)
3. **Classification**: Routes to appropriate language classifier
4. **Fact-Checking**: Similarity matcher verifies against known sources
5. **Credibility**: Assesses source credibility if available
6. **Aggregation**: Orchestrator combines all results
7. **Output**: Returns comprehensive analysis

## 🐳 Docker Services

### Service Ports
- Tamil Classifier: 1000
- Sinhala Classifier: 2000
- Similarity Matcher: 3000
- Credibility Predictor: 4000
- Orchestrator: 5000
- Frontend: 8080

### Docker Commands

```bash
# Start specific service
docker-compose up tamil-classifier

# View logs
docker-compose logs tamil-classifier

# Rebuild service
docker-compose up --build tamil-classifier

# Stop all
docker-compose down
```

## 🔍 Monitoring & Logging

- **Health Checks**: Automatic health monitoring every 30 seconds
- **Logging**: JSON-formatted logs with size limits (10MB, 3 files)
- **Restart Policy**: `unless-stopped` for automatic recovery

## 🚀 Deployment

### Production Deployment

1. **Build production images**:
   ```bash
   docker-compose -f docker-compose.yml up --build
   ```

2. **Use reverse proxy** (nginx recommended):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8080;
           proxy_set_header Host $host;
       }

       location /api {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
       }
   }
   ```

3. **SSL Configuration**: Use certbot or similar for HTTPS

### Scaling

- **Horizontal Scaling**: Run multiple instances behind load balancer
- **GPU Support**: Enable CUDA for Tamil classifier if GPU available
- **Database**: Consider adding database for result caching

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

## 📝 License

[Add license information]

## 📞 Support

For issues and questions:
- Check service logs: `docker-compose logs <service-name>`
- Verify model files are present
- Ensure all dependencies are installed
- Check network connectivity between services

## 🔄 Updates & Maintenance

- **Model Updates**: Replace model files in respective directories
- **Dependency Updates**: Update requirements.txt and rebuild containers
- **Data Updates**: Update verified sources for similarity matcher
- **Security**: Regularly update base images and dependencies

---

**Note**: This system is designed for Tamil and Sinhala language fake news detection. For other languages, additional classifiers would need to be developed following the same architecture pattern.
