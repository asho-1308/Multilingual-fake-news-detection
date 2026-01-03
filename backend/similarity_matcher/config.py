import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# HF token (not strictly required for local model load, but kept for consistency)
HF_TOKEN = os.getenv("HF_TOKEN", "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")

# Paths (relative to this backend folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.getenv(
    "MODEL_DIR",
    os.path.join(BASE_DIR, "models", "fine_tuned_labse_multilingual")
)

FAISS_INDEX_PATH = os.getenv(
    "FAISS_INDEX_PATH",
    os.path.join(BASE_DIR, "artifacts", "claims_index_multilingual_refined_v2.faiss")
)

DATA_CSV = os.getenv(
    "DATA_CSV",
    os.path.join(BASE_DIR, "artifacts", "verified_sources_multilingual_v2.csv")
)

# Semantic search parameters (same as notebook)
TOP_K = int(os.getenv("TOP_K", "3"))
MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", str(TOP_K * 5)))

# Server config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "3000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
