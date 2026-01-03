import os
import json
import numpy as np
import pandas as pd
import faiss

from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

def detect_language_safe(text: str) -> str:
    try:
        if not text:
            return "en"
        sinhala_count = sum(1 for ch in text if "\u0D80" <= ch <= "\u0DFF")
        tamil_count = sum(1 for ch in text if "\u0B80" <= ch <= "\u0BFF")
        if sinhala_count > tamil_count and sinhala_count > 0:
            return "si"
        if tamil_count > sinhala_count and tamil_count > 0:
            return "ta"
        return "en"
    except:
        return "en"


class SemanticVerifierService:
    def __init__(self):
        self.data_csv = os.getenv("DATA_CSV", "artifacts/verified_sources_multilingual_v3_300.csv")
        self.faiss_path = os.getenv("FAISS_INDEX", "artifacts/claims_index_multilingual_v3_300.faiss")

        self.model_dir = os.getenv("MODEL_DIR", "models/fine_tuned_labse_multilingual")
        self.model_name = os.getenv("MODEL_NAME", "sentence-transformers/LaBSE")

        self.top_k_default = int(os.getenv("TOP_K_DEFAULT", "3"))
        self.max_candidates_mult = int(os.getenv("MAX_CANDIDATES_MULT", "5"))

        hf_token = os.getenv("HF_TOKEN", "").strip() or None

        print("🔧 Loading dataset from:", self.data_csv)
        if not os.path.exists(self.data_csv):
            raise FileNotFoundError(f"DATA_CSV not found: {self.data_csv}")

        self.df = pd.read_csv(self.data_csv, encoding="utf-8")
        self.df = self.df.dropna(subset=["claim"]).reset_index(drop=True)

        # Load model (prefer local fine-tuned if valid)
        self.model = None

        # ✅ try local model first
        if os.path.isdir(self.model_dir) and os.path.exists(os.path.join(self.model_dir, "modules.json")):
            try:
                print("🔧 Loading SentenceTransformer model from:", self.model_dir)
                self.model = SentenceTransformer(self.model_dir)
                print("✅ Loaded local SentenceTransformer model.")
            except Exception as e:
                print("⚠️ Failed loading local model. Fallback to pretrained.")
                print("Reason:", e)

        # ✅ fallback to online pretrained (with token)
        if self.model is None:
            print("🔧 Loading pretrained model:", self.model_name)
            self.model = SentenceTransformer(self.model_name, token=hf_token)
            print("✅ Loaded pretrained model.")

        # Load FAISS index
        print("🔧 Loading FAISS index from:", self.faiss_path)
        if not os.path.exists(self.faiss_path):
            raise FileNotFoundError(f"FAISS index not found: {self.faiss_path}")

        self.index = faiss.read_index(self.faiss_path)

        # sanity check
        if self.index.ntotal != len(self.df):
            print(f"⚠️ Warning: index vectors={self.index.ntotal} but df rows={len(self.df)} (should match).")

        print(f"✅ SemanticVerifierService ready with {len(self.df)} claims")

    def _semantic_search_unique(self, claim: str, top_k: int, max_candidates: int):
        emb = self.model.encode([claim], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(emb)

        D, I = self.index.search(emb, k=max_candidates)

        seen = set()
        results = []

        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self.df):
                continue
            row = self.df.iloc[idx]
            url = str(row.get("url", "")).strip()
            key = url if url else f"id-{int(row.get('id', idx))}"
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "similarity": float(dist),
                "claim": str(row.get("claim", "")),
                "verdict": str(row.get("verdict", "Unknown")),
                "source": str(row.get("source", "")),
                "url": str(row.get("url", "")),
            })

            if len(results) >= top_k:
                break

        return results

    def _aggregate_verdict(self, results):
        if not results:
            return "No Match", 0.0

        true_count = sum(1 for r in results if r["verdict"] in ["True", "Partly True"])
        false_count = sum(1 for r in results if r["verdict"] == "False")

        if true_count > false_count:
            return "Likely TRUE", round(true_count / len(results), 4)
        if false_count > true_count:
            return "Likely FALSE", round(false_count / len(results), 4)

        return "UNCERTAIN", 0.5

    def verify(self, claim: str, top_k: int = None):
        if top_k is None:
            top_k = self.top_k_default

        max_candidates = max(top_k * self.max_candidates_mult, top_k)

        lang = detect_language_safe(claim)
        neighbors = self._semantic_search_unique(claim, top_k=top_k, max_candidates=max_candidates)
        final_verdict, confidence = self._aggregate_verdict(neighbors)

        return {
            "input_claim": claim,
            "detected_language": lang,
            "final_verdict": final_verdict,
            "confidence": float(confidence),
            "top_k": int(top_k),
            "neighbors": neighbors,
        }
