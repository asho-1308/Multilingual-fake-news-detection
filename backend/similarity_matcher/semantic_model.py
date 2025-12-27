import faiss
import numpy as np
import pandas as pd

from sentence_transformers import SentenceTransformer

from config import MODEL_DIR, FAISS_INDEX_PATH, DATA_CSV, TOP_K, MAX_CANDIDATES
from language_utils import detect_language_safe


class SemanticVerifierService:
    """
    Backend service that loads:
      - fine-tuned LaBSE model (or base LaBSE in that folder)
      - FAISS index with embeddings
      - dataset CSV (verified_sources_multilingual_v2.csv)

    And exposes a method verify_claim() that mirrors your notebook's MultilingualVerifier.verify.
    """

    def __init__(self):
        print("🔧 Loading dataset from:", DATA_CSV)
        self.df = pd.read_csv(DATA_CSV, encoding="utf-8")
        self.df = self.df.reset_index(drop=True)

        print("🔧 Loading SentenceTransformer model from:", MODEL_DIR)
        self.model = SentenceTransformer(MODEL_DIR)

        print("🔧 Loading FAISS index from:", FAISS_INDEX_PATH)
        self.index = faiss.read_index(FAISS_INDEX_PATH)

        if self.index.ntotal != len(self.df):
            print(f"⚠️ Warning: FAISS vectors ({self.index.ntotal}) != rows in df ({len(self.df)})")
            # Still works if the order matches; just a warning.

        print(f"✅ SemanticVerifierService ready with {len(self.df)} claims")

    def _semantic_search_unique(self, claim: str, top_k: int = TOP_K, max_candidates: int = MAX_CANDIDATES):
        """
        Same logic as your notebook:
        - encode query
        - search in FAISS
        - enforce unique URLs / IDs for top-k results
        """
        emb = self.model.encode([claim], convert_to_numpy=True)
        faiss.normalize_L2(emb)

        D, I = self.index.search(emb.astype('float32'), k=max_candidates)

        seen_keys = set()
        results = []

        for dist, idx in zip(D[0], I[0]):
            if idx >= len(self.df):
                continue

            row = self.df.iloc[idx]
            url = str(row.get('url', '')).strip()
            key = url if url else f"id-{int(row.get('id', idx))}"

            if key in seen_keys:
                continue
            seen_keys.add(key)

            results.append({
                "similarity": float(dist),
                "claim": row["claim"],
                "verdict": row["verdict"],
                "source": row["source"],
                "url": row["url"],
            })

            if len(results) >= top_k:
                break

        return results

    def verify_claim(self, claim: str, top_k: int = TOP_K):
        """
        High-level API used by Flask endpoint.
        Returns JSON-serializable dict:
        {
          input_claim, detected_language, final_verdict, confidence, top_k, neighbors[]
        }
        """
        lang = detect_language_safe(claim)
        nn_results = self._semantic_search_unique(claim, top_k=top_k)

        true_like = ["True", "Partly True"]
        false_like = ["False"]

        true_count = sum(1 for r in nn_results if r["verdict"] in true_like)
        false_count = sum(1 for r in nn_results if r["verdict"] in false_like)

        if true_count > false_count:
            final_verdict = "Likely TRUE"
            confidence = true_count / max(1, len(nn_results))
        elif false_count > true_count:
            final_verdict = "Likely FALSE"
            confidence = false_count / max(1, len(nn_results))
        else:
            final_verdict = "UNCERTAIN"
            confidence = 0.0

        return {
            "input_claim": claim,
            "detected_language": lang,
            "final_verdict": final_verdict,
            "confidence": round(confidence, 3),
            "top_k": len(nn_results),
            "neighbors": nn_results,
        }
