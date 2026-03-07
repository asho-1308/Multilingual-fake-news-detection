# Multilingual Fake News Detection System: Deep Technical Methodology

## 1. System Architecture & High-Level Design
The system employs a **De-coupled Microservices Architecture**, enabling horizontal scalability and independent optimization for specialized linguistic tasks. It consists of six primary layers:

*   **Ingestion Layer**: A Chrome Extension and a React/TypeScript Web Frontend (Vite-powered).
*   **Orchestration Layer**: A Flask-based central controller performing real-time language detection and request routing.
*   **Classification Layer**: Deep learning and ML models specialized for Tamil (BERT) and Sinhala (Random Forest).
*   **Verification Layer (Similarity Matcher)**: Semantic search against a verified database using vector embeddings.
*   **Contextual Layer (Credibility Predictor)**: A metadata-driven source reliability model.
*   **Ensemble Layer**: A heuristic engine that aggregates signals using a weighted voting system.

---

## 2. Component Deep Dive

### A. Tamil Classifier: BERT-based Linguistic Analysis
The Tamil classification component leverages a Transformer-based architecture specifically fine-tuned for the Tamil language.
*   **Model Architecture**: Utilizes **BERT (Bidirectional Encoder Representations from Transformers)** for sequence classification (`BertForSequenceClassification`). It features 12 hidden layers, 12 attention heads, and a hidden size of 768.
*   **Preprocessing (Indic NLP)**:
    *   **Normalization**: Employs `IndicNormalizerFactory` from the **Indic NLP Library** to standardize Tamil Unicode characters (`\u0B80-\u0BFF`).
    *   **Text Cleaning**: A regex-based pipeline removes URLs and non-Tamil characters to reduce noise before tokenization.
*   **Computer Vision (EasyOCR)**:
    *   Handles image-based news using **EasyOCR** (Tamil `ta` and English `en`).
    *   **Enhanced Detection**: Applies OpenCV-based preprocessing (Grayscale + **Otsu's Thresholding**) if initial OCR fails.

### B. Sinhala Classifier: Classical Machine Learning
The Sinhala detection module relies on statistical machine learning enhanced by language-specific feature engineering.
*   **Core Model**: A **Random Forest Classifier** trained on the *LIRNEasia Misinformation Corpus*.
*   **Feature Engineering**: Uses **TF-IDF (Term Frequency-Inverse Document Frequency)** vectorization with custom cleaning for the Sinhala Unicode range (`\u0D80-\u0DFF`).
*   **Stopword Filtering**: Employs a curated list of Sinhala stopwords (e.g., "සහ", "හා", "ද") to optimize signal-to-noise ratios.

### C. Semantic Similarity Matcher (Fact-Checking)
This module performs fact-checking by comparing input claims against a verified database using dense vector embeddings.
*   **Model**: Utilizes **LaBSE (Language-Agnostic BERT Sentence Embedding)** for cross-lingual vector representation.
*   **Vector Search (FAISS)**:
    *   Embeddings are **L2-normalized** and queried against a **FAISS (Facebook AI Similarity Search)** index.
    *   **Strategy**: It performs a search for the top $k=3$ unique neighbors, filtering out duplicate source URLs to ensure diverse evidence.
*   **Aggregation Logic**: The confidence is calculated as the ratio of the majority class (True vs. False) among the retrieved neighbors.

### D. Credibility Predictor: Source Metadata Analysis
Assesses the reliability of the news source itself using a metadata-driven Random Forest model (100 estimators).
*   **Feature Set**: 
    1. `past_fake`: Historical count of identified misinformation.
    2. `past_real`: Historical count of verified news.
    3. `domain_age_years`: Longevity of the source domain.
    4. `followers`: Metric for social reach/authority.
*   **Encoding**: Uses `LabelEncoder` for categorical language metadata before classification.

---

## 3. Specialized Chrome Extension Feature
The extension acts as an **Active DOM Content Analyzer**:
*   **DOM Injection**: Uses a **Content Script** to scan for headlines (`h1-h6`, `role="heading"`, and headline-related classes).
*   **Overlay UI**: Injects dynamically positioned `div` elements next to news headers. It uses `getBoundingClientRect()` for precise anchoring and custom-prefixed CSS (`fnd-`) to prevent style collisions with the host page.
*   **CORS Management**: Communicates with the local orchestrator via `fetch`, enabled by **Cross-Origin Resource Sharing** middleware on the backend.

---

## 4. Ensemble Logic & Weighting Strategy
The Orchestrator synthesizes signals to produce a unified verdict.
*   **Weighting Math**:
    *   **Similarity Matcher**: Priority weight **1.2** (highest weight due to factual grounding).
    *   **Linguistic Classifier**: Base weight **1.0** (if confidence $> 0.8$) or **0.7**.
    *   **Credibility Predictor**: Supporting weight **0.5 - 0.8**.
*   **Final Confidence Calculation**:
    The system uses a weighted average of the winning class signals:
    $$Score_{final} = \frac{\sum (Confidence_i \times Weight_i)}{\sum Weight_i}$$
    The score is normalized and clamped to the range $[0.0, 1.0]$.

---

## 5. Technical Innovation for Research
The primary innovation lies in the **Cross-lingual Ensemble Strategy**. By decoupling linguistic analysis (style) from semantic verification (facts), the system can flag misinformation even when:
1. The specific text has never been seen before (via linguistics).
2. The claim is brand-new but comes from a historically unreliable source (via credibility).
3. The news is translated across Tamil and Sinhala (via cross-lingual LaBSE embeddings).

This hybrid approach effectively addresses the "cold-start" problem in low-resource language fake news detection.

