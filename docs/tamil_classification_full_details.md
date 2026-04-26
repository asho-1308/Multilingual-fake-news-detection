# Tamil Fake News Classification — Full Details

This document describes the Tamil fake-news classification project from first principles, documents how training is (re)produced in the notebooks included in this repository, compares candidate models, and summarizes progress and next steps.

## Overview
- Goal: classify Tamil news headlines (or short items) as real vs fake.
- Artifacts in this repo: a trained BERT-style model and inference service with OCR support, plus several training notebooks for experiments.

## Important files and notebooks
- Model artifacts: [backend/tamil_classifier/my_tamil_fake_news_model](backend/tamil_classifier/my_tamil_fake_news_model)
- Inference service: [backend/tamil_classifier/main.py](backend/tamil_classifier/main.py)
- OCR models: [backend/tamil_classifier/ocr_models](backend/tamil_classifier/ocr_models)
- Dataset candidate: [data/Tamil-News-Headlines.csv](data/Tamil-News-Headlines.csv)
- Training /实验 notebooks: [notebooks/tamil_fakenews_detection/FakenewsDetectionTamil (3).ipynb](notebooks/tamil_fakenews_detection/FakenewsDetectionTamil%20(3).ipynb), [notebooks/tamil_fakenews_detection/FakenewsDetectionTamil (4).ipynb](notebooks/tamil_fakenews_detection/FakenewsDetectionTamil%20(4).ipynb), [notebooks/tamil_fakenews_detection/FakenewsDetectionTamil using Muril.ipynb](notebooks/tamil_fakenews_detection/FakenewsDetectionTamil%20using%20Muril.ipynb), [notebooks/tamil_fakenews_detection/FakenewsDetectionTamil_using_Muril_final.ipynb](notebooks/tamil_fakenews_detection/FakenewsDetectionTamil_using_Muril_final.ipynb)

## Dataset
- Location: [data/Tamil-News-Headlines.csv](data/Tamil-News-Headlines.csv).
- Required fields: text (headline), label (binary: fake/real). If labels use other strings, map them to binary ids.
- Recommended checks:
  - Inspect class balance (counts per label).
  - Remove exact duplicates and near-duplicates.
  - Normalize whitespace and punctuation.
  - Record provenance, collection date, and license.

## Preprocessing (training vs inference differences)
- Unicode normalization: NFC or NFKC; remove control characters.
- Indic normalization: use `indic-nlp-library` normalizers included under `indic_nlp_resources`.
- Tokenization: use the provided tokenizer files in `my_tamil_fake_news_model` to ensure token IDs match the model.
- Text cleaning used in inference (`main.py`): keep Tamil Unicode range (U+0B80–U+0BFF), strip non-Tamil characters unless useful, remove excessive punctuation, trim length.
- For training: consider data augmentation for low-resource settings (back-translation or synonym replacement), but avoid label leakage.

## Tokenization and Vocabulary
- The model directory contains `tokenizer.json`, `vocab.txt`, and `tokenizer_config.json`. Use the Hugging Face `AutoTokenizer.from_pretrained()` pointing to the local model folder to ensure identical tokenization.
- Recommended max length: 256--512 based on `max_position_embeddings` (512) in the saved model's `config.json`.

## Candidate Models and Comparison
We recommend comparing at least the following model families; the notebooks already include experiments with MuRIL variants.

- BERT-base (monolingual or pre-trained multilingual variant)
  - Pros: well-known baseline, moderately small, stable performance with fine-tuning.
  - Cons: monolingual BERT for Tamil might be unavailable; multilingual BERT may have limited Tamil representations.

- mBERT (multilingual BERT)
  - Pros: multilingual, zero-shot transfer possible.
  - Cons: shared vocab reduces language-specific tokens; sometimes weaker for single language.

- MuRIL (Multilingual Representations for Indian Languages)
  - Pros: trained specifically for Indian languages, often better than mBERT on Indic languages.
  - Cons: larger model sizes; compute cost.

- DistilBERT (distilled model)
  - Pros: faster inference, smaller footprint.
  - Cons: possibly lower accuracy.

- Custom fine-tuned BERT (the repository `my_tamil_fake_news_model`)
  - Pros: artifact available; model architecture and tokenizer stored.
  - Cons: training hyperparameters, exact dataset split and evaluation results are not included in the folder and must be reproduced or documented.

Comparison Template (fill with measured values after training/reproduction):

| Model | Params | Inference Latency | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| MuRIL | ~110M |  |  |  |  |  |
| mBERT | ~110M |  |  |  |  |  |
| Custom BERT | (see config) |  |  |  |  |  |
| DistilBERT | ~66M |  |  |  |  |  |

## Training: reproducible recipe (notebook steps)
1. Environment: create virtualenv and install requirements from `backend/tamil_classifier/requirements.txt` (or use a separate `requirements-train.txt` with `datasets` and `transformers`).

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/tamil_classifier/requirements.txt
pip install datasets transformers accelerate scikit-learn pandas
```

2. Prepare dataset CSV with `text` and `label` columns. Split into train/val/test (e.g., 80/10/10) using a fixed seed.

3. Tokenize using the model tokenizer:

```python
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('backend/tamil_classifier/my_tamil_fake_news_model')
tokens = tokenizer(texts, padding='max_length', truncation=True, max_length=256)
```

4. Fine-tune with `Trainer` or HF `accelerate`. Example hyperparameters:
  - optimizer: AdamW
  - lr: 2e-5
  - batch size: 16
  - epochs: 3
  - weight decay: 0.01
  - warmup steps: 0.06 * total_steps (or use proportion)

5. Save best checkpoint by validation F1. Log metrics to CSV or TensorBoard.

6. After training, evaluate on the held-out test set and compute accuracy, precision, recall, F1, and confusion matrix.

## Evaluation and Analysis
- Use stratified splits to preserve class balance.
- Report per-class metrics, macro-average F1, and Cohen's kappa if needed.
- Plot confusion matrix and common error types.
- Perform qualitative error analysis: sample misclassified items and identify patterns (ambiguous wording, sarcasm, domain shift).

## Deployment / Inference
- The inference API is in [backend/tamil_classifier/main.py](backend/tamil_classifier/main.py). Key points:
  - Model loading uses `transformers` pipeline for `text-classification` pointing to the local model folder.
  - OCR is supported through EasyOCR; OCR models live in [backend/tamil_classifier/ocr_models](backend/tamil_classifier/ocr_models).
  - Endpoints: `/health`, `/predict`, `/predict_image_upload`, `/predict_image_url`.

## Reproducing the Notebooks
- Open the notebooks in `notebooks/tamil_fakenews_detection` and run cells in order. Notebooks with MuRIL in their titles already contain experiments using MuRIL-based tokenizers and models.
- If notebooks use GPU, ensure CUDA drivers and a GPU-enabled environment.

Quick commands to run a training notebook with `nbconvert` (non-interactive):

```bash
pip install jupyter nbconvert
jupyter nbconvert --to notebook --execute "notebooks/tamil_fakenews_detection/FakenewsDetectionTamil_using_Muril.ipynb" --output executed_notebook.ipynb
```

## Progress log (what's available and gaps)
- Available: inference service, model artifacts (weights & tokenizer), OCR models, multiple training notebooks with MuRIL experiments, dataset CSV.
- Missing / to reproduce fully:
  - A canonical `train.py` script with the exact hyperparameters used to produce `my_tamil_fake_news_model` (not present in `tamil_classifier` folder).
  - Training logs (loss curves, per-epoch metrics) and test-set evaluation reports.
  - Explicit `id2label` mapping in model config (README indicates mapping but config may not include it).

## Recommended next steps
1. Run the MuRIL notebook end-to-end and capture training logs and final test metrics.
2. Fill the comparison table above with measured values.
3. Add `id2label` to saved model config or separately document label mapping.
4. Save evaluation artifacts (CSV of metrics, confusion matrix PNGs) into `docs/` for inclusion in the thesis.

## Appendix — Example training command (HF Trainer)

```bash
python run_glue_like_finetune.py \
  --model_name_or_path google/muril-base-cased \
  --train_file data/Tamil-News-Headlines.csv \
  --validation_split_percentage 10 \
  --do_train --do_eval \
  --per_device_train_batch_size 16 \
  --learning_rate 2e-5 \
  --num_train_epochs 3 \
  --output_dir output/muril_tamil
```

---

This file was generated to document the Tamil classification pipeline, the notebooks included, a reproducible training recipe, and the model comparison template. After you run the MuRIL notebook (or ask me to run experiments), I will update the comparison table and add concrete metric values and figures.

## Detailed Technical Appendix (Deep Dive)

### 1. Data cleaning and preprocessing (detailed)
Below are recommended, reproducible preprocessing steps you should run before training. These steps appear in the notebooks but are consolidated here as copy-paste-ready code.

Python snippet — dataset load, basic cleaning, and splits:

```python
import pandas as pd
from sklearn.model_selection import train_test_split
RANDOM_SEED = 42

df = pd.read_csv('data/Tamil-News-Headlines.csv')
df = df.rename(columns={col: col.strip() for col in df.columns})
df = df.dropna(subset=['text','label']).drop_duplicates(subset=['text'])

# Normalize labels if necessary
df['label'] = df['label'].map({'fake':1,'real':0}).astype(int)

train_df, temp_df = train_test_split(df, test_size=0.2, stratify=df['label'], random_state=RANDOM_SEED)
val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df['label'], random_state=RANDOM_SEED)

train_df.to_csv('data/train.csv', index=False)
val_df.to_csv('data/val.csv', index=False)
test_df.to_csv('data/test.csv', index=False)
```

Unicode normalization and Indic text cleaning:

```python
import unicodedata
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory

def normalize_text(text):
  # NFC normalize
  text = unicodedata.normalize('NFC', str(text))
  # Indic normalization
  normalizer = IndicNormalizerFactory().get_normalizer("ta")
  text = normalizer.normalize(text)
  # optionally filter non-Tamil chars
  return text

train_df['text'] = train_df['text'].apply(normalize_text)
```

Tokenization (use local tokenizer to match inference model):

```python
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('backend/tamil_classifier/my_tamil_fake_news_model')
def tokenize_batch(texts, max_len=256):
  return tokenizer(texts, padding='max_length', truncation=True, max_length=max_len)
```

### 2. Training script example (Hugging Face Trainer)
Below is a condensed training script using the HF `Trainer`. Save as `train_tamil.py` and adapt paths/hyperparams.

```python
from datasets import load_dataset, Dataset
from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

train = Dataset.from_pandas(pd.read_csv('data/train.csv'))
val = Dataset.from_pandas(pd.read_csv('data/val.csv'))

model = AutoModelForSequenceClassification.from_pretrained('google/muril-base-cased', num_labels=2)
tokenizer = AutoTokenizer.from_pretrained('google/muril-base-cased')

def preprocess(examples):
  return tokenizer(examples['text'], truncation=True, padding='max_length', max_length=256)

train = train.map(preprocess, batched=True)
val = val.map(preprocess, batched=True)

def compute_metrics(pred):
  labels = pred.label_ids
  preds = np.argmax(pred.predictions, axis=1)
  precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='macro')
  acc = accuracy_score(labels, preds)
  return {'accuracy': acc, 'precision': precision, 'recall': recall, 'f1': f1}

args = TrainingArguments(
  output_dir='output/muril_tamil',
  evaluation_strategy='epoch',
  save_strategy='epoch',
  learning_rate=2e-5,
  per_device_train_batch_size=16,
  per_device_eval_batch_size=32,
  num_train_epochs=3,
  weight_decay=0.01,
  seed=42,
)

trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val, compute_metrics=compute_metrics)
trainer.train()
trainer.save_model('output/muril_tamil/final')
```

### 3. Hyperparameter recommendations and sweep plan
- Baseline: lr=2e-5, batch=16, epochs=3. If underfitting, raise epochs to 5.
- For hyperparameter tuning, sweep over lr in [5e-6, 2e-5, 5e-5], batch in [8,16,32], max_len in [128,256,512].
- Use early stopping on validation F1 with patience=2.

### 4. Handling class imbalance
- If dataset is imbalanced, apply one or more:
  - Class weights in loss: set `weight=torch.tensor([w0,w1]).to(device)` in `CrossEntropyLoss`.
  - Oversampling minority class in the training split (or use `ImbalancedDatasetSampler`).
  - Focal loss for hard-example focusing.

### 5. Evaluation metrics (formulas)
- Accuracy = (TP + TN) / (TP + TN + FP + FN)
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * (Precision * Recall) / (Precision + Recall)
- Use macro-averaged F1 for class-imbalanced datasets.

### 6. Cross-validation and statistical robustness
- Use stratified K-fold (K=5) to obtain stable estimates when dataset is small. Aggregate metrics and report mean ± std.

### 7. Explainability
- Attention probes: visualize token-level attention weights from the last layer pooled outputs.
- Post-hoc methods: LIME and SHAP can explain individual predictions; use `shap` with `transformers` wrappers or `LIME` for text.

Example SHAP usage snippet:

```python
import shap
from transformers import pipeline
pipe = pipeline('text-classification', model='output/muril_tamil/final', tokenizer='output/muril_tamil/final')
def f(texts):
  return [x['score'] for x in pipe(texts, truncation=True)]
explainer = shap.Explainer(f, tokenizer)
shap_values = explainer(["கட்டுரை உதாரணம்"])
shap.plots.text(shap_values[0])
```

### 8. Inference optimization
- Export to ONNX and use `onnxruntime` for faster CPU inference.
- Apply quantization (dynamic/static) with `optimum` or `transformers` quantization tools.
- Batch requests server-side; reuse tokenizer instance.

### 9. Deployment and scaling notes
- Dockerfile already included. For production:
  - Use a lightweight server (Uvicorn/Gunicorn with multiple workers) behind a reverse proxy.
  - Add health checks, readiness probes, and liveness probes in Kubernetes manifests (see `k8s/` folder).
  - Use GPU nodes for batch scoring, CPU nodes for low-latency single predictions with optimized models.

### 10. Logging, monitoring, and experiment tracking
- Use Weights & Biases, MLflow, or plain CSV/TensorBoard to log hyperparameters, runs, and metrics.
- Persist best model artifacts with explicit `id2label` in `config.json`:

```json
"id2label": {"0": "real", "1": "fake"},
"label2id": {"real":0, "fake":1}
```

### 11. Reproducibility checklist
- Record `transformers` and `datasets` versions, Python version, and CUDA/cuDNN versions.
- Fix seeds for `numpy`, `torch`, and HF `set_seed(42)`.
- Save tokenizer and model with `save_pretrained()` and commit the `config.json` with `id2label`.

### 12. Ethical considerations (expanded)
- Document data sources and annotation protocol. If annotations were crowdsourced, include instructions and inter-annotator agreement scores.
- Discuss false-positive vs false-negative tradeoffs: false positives (labeling real as fake) can harm trust; false negatives (missing fake) can spread misinformation.

### 13. Deliverables to produce next
1. Execute the MuRIL notebook (or `train_tamil.py`) to produce a reproducible model and evaluation artifacts.
2. Fill the model comparison table in this document with measured metrics and inference latencies.
3. Save confusion matrices and error-analysis samples into `docs/figures/`.

---

When you confirm, I will run `backend/tamil_classifier/test_api.py` to collect sample predictions and then (if requested) execute the MuRIL notebook to reproduce training.
