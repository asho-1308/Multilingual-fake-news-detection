import os
import json
import numpy as np
import pandas as pd
import faiss
import requests

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
        self.serpapi_key = os.getenv("SERPAPI_KEY", "").strip()

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

        # ✅ fallback to online pretrained
        if self.model is None:
            print("🔧 Loading pretrained model:", self.model_name)
            try:
                # Try without token for compatibility with older SentenceTransformer versions
                self.model = SentenceTransformer(self.model_name)
            except TypeError:
                # Fallback if it somehow expects token but failed above
                self.model = SentenceTransformer(self.model_name, use_auth_token=hf_token)
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

        # Only count results with a high enough similarity to be meaningful
        # A match > 0.9 is almost certainly the same story
        # A match > 0.7 is likely the same topic
        best_sim = results[0]["similarity"] if results else 0.0
        
        if best_sim > 0.8:
            # If the best match is very high, use its specific verdict
            top_verdict = results[0].get("verdict", "Unknown")
            if any(x in top_verdict.lower() for x in ["true", "article", "real", "සත්‍ය"]):
                return "VERIFIED REAL", round(best_sim, 4)
            if any(x in top_verdict.lower() for x in ["false", "fake", "fake news", "අසත්‍ය"]):
                return "VERIFIED FAKE", round(best_sim, 4)
            return "MATCH FOUND", round(best_sim, 4)

        if best_sim < 0.5:
            return "UNCERTAIN", 0.3

        # For middle-range similarities (0.5 to 0.8), use the weighted logic
        significant_results = [r for r in results if r["similarity"] > 0.5]
        if false_count > true_count:
            return "Likely FALSE", round(false_count / len(significant_results), 4)
        
        # If it's a tie among significant results (e.g. 1 True, 1 False)
        return "UNCERTAIN", 0.5

    def _scrape_online_news(self, claim: str):
        """Scrapes online news via SerpApi if no match is found in CSV."""
        if not self.serpapi_key or self.serpapi_key == "YOUR_SERP_API_KEY_HERE":
            print(f"DEBUG: [SM] ⚠️ SerpApi key not configured or placeholder used. Key found: '{self.serpapi_key[:5]}...'")
            return []

        print(f"DEBUG: [SM] 🔍 Searching online for: {claim}")
        try:
            params = {
                "q": claim,
                "tbm": "nws",  # News search
                "api_key": self.serpapi_key,
                "num": 3
            }
            # Give the external API more time
            response = requests.get("https://serpapi.com/search", params=params, timeout=15)
            print(f"DEBUG: [SM] SerpApi response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"DEBUG: [SM] ⚠️ SerpApi failed with status {response.status_code}. Response: {response.text[:200]}")
                return []

            data = response.json()
            news_results = data.get("news_results", [])
            print(f"DEBUG: [SM] Found {len(news_results)} news results from SerpApi")
            
            online_neighbors = []
            # Encode claim once outside the loop
            emb_claim = self.model.encode([claim], convert_to_numpy=True).astype("float32")
            faiss.normalize_L2(emb_claim)

            for item in news_results[:3]:
                title = item.get("title", "")
                link = item.get("link", "")
                source = item.get("source", "Online News")
                
                # Calculate similarity for the online title
                emb_title = self.model.encode([title], convert_to_numpy=True).astype("float32")
                faiss.normalize_L2(emb_title)
                
                # Dot product of normalized vectors = Cosine Similarity
                sim = float(np.dot(emb_claim, emb_title.T)[0][0])
                print(f"DEBUG: [SM] Online match: '{title[:30]}...' Similarity: {sim:.4f}")
                
                online_neighbors.append({
                    "similarity": sim,
                    "claim": title,
                    "verdict": "News Article", 
                    "source": source,
                    "url": link,
                    "is_online": True
                })
            
            # Sort by similarity
            online_neighbors.sort(key=lambda x: x['similarity'], reverse=True)
            return online_neighbors
        except Exception as e:
            print(f"DEBUG: [SM] ⚠️ Online search error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def verify(self, claim: str, top_k: int = None):
        if top_k is None:
            top_k = self.top_k_default

        max_candidates = max(top_k * self.max_candidates_mult, top_k)

        lang = detect_language_safe(claim)
        neighbors = self._semantic_search_unique(claim, top_k=top_k, max_candidates=max_candidates)
        
        # Trigger online scraping if no strong match in CSV
        # Threshold: if the best single match is < 0.6, try online
        best_sim_csv = neighbors[0]['similarity'] if neighbors else 0
        is_fallback = False
        
        if best_sim_csv < 0.6:
            online_neighbors = self._scrape_online_news(claim)
            if online_neighbors:
                # Merge and keep top_k best results overall
                neighbors = sorted(online_neighbors + neighbors, key=lambda x: x['similarity'], reverse=True)[:top_k]
                is_fallback = True

        final_verdict, confidence = self._aggregate_verdict(neighbors)

        # If Online Scraper found a match and aggregate didn't catch it
        if is_fallback and neighbors and neighbors[0].get('is_online'):
            best_sim = neighbors[0]['similarity']
            if best_sim > 0.6:
                final_verdict = "VERIFIED REAL (ONLINE)"
                confidence = best_sim

        return {
            "input_claim": claim,
            "detected_language": lang,
            "final_verdict": final_verdict,
            "confidence": float(confidence),
            "top_k": int(top_k),
            "neighbors": neighbors,
            "used_online_search": is_fallback
        }
