import os
import json
import numpy as np
import pandas as pd
import faiss
import requests
import re

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

            # Normalize similarity: FAISS may return inner-product or L2 distances.
            sim_val = float(dist)
            try:
                # If dist looks like a small L2 distance (close to 0), convert to similarity
                if sim_val >= 0.0 and sim_val <= 0.5:
                    # assume this is L2-distance-ish; closer to 0 => more similar
                    sim = max(0.0, 1.0 - sim_val)
                else:
                    # otherwise treat as already a similarity (e.g., inner-product cosine)
                    sim = sim_val
            except Exception:
                sim = sim_val

            # Exact-match override: if the stored claim/title text matches the input claim closely,
            # treat as perfect match (helps cases where FAISS returned small distance values)
            try:
                n_claim = self._normalize_text(claim)
                row_claim = str(row.get("claim", ""))
                n_row = self._normalize_text(row_claim)
                if n_claim and n_row and (n_claim in n_row or n_row in n_claim):
                    sim = 1.0
            except Exception:
                pass

            results.append({
                "similarity": float(sim),
                "claim": str(row.get("claim", "")),
                "title": str(row.get("claim", "")),
                "verdict": str(row.get("verdict", "Unknown")),
                "source": str(row.get("source", "")),
                "url": str(row.get("url", "")),
            })

            if len(results) >= top_k:
                break

        return results

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        # lowercase, remove punctuation, collapse whitespace
        txt = text.lower()
        try:
            import unicodedata
            chars = []
            for ch in txt:
                cat = unicodedata.category(ch)
                # Skip punctuation (P*) and symbols (S*)
                if cat.startswith("P") or cat.startswith("S"):
                    chars.append(" ")
                else:
                    chars.append(ch)
            txt = "".join(chars)
        except Exception:
            # Fallback: remove common ASCII punctuation
            txt = re.sub(r"[\"'`\[\]{}()<>@,;:.!?\\/\\\\\-—–<>]", " ", txt)
        txt = re.sub(r"\s+", " ", txt)
        return txt.strip()

    def _aggregate_verdict(self, results):
        if not results:
            return "No Match", 0.0

        best_sim = results[0]["similarity"] if results else 0.0
        
        if best_sim > 0.8:
            top_verdict = results[0].get("verdict", "Unknown")
            if any(x in top_verdict.lower() for x in ["true", "article", "real", "සත්‍ය"]):
                return "VERIFIED REAL", round(best_sim, 4)
            if any(x in top_verdict.lower() for x in ["false", "fake", "fake news", "අසත්‍ය"]):
                return "VERIFIED FAKE", round(best_sim, 4)
            return "MATCH FOUND", round(best_sim, 4)

        if best_sim < 0.5:
            return "UNCERTAIN", 0.3

        # For middle-range similarities (0.5 to 0.8), count the verdicts
        significant_results = [r for r in results if r["similarity"] > 0.5]
        false_count = sum(1 for r in significant_results if any(x in r["verdict"].lower() for x in ["false", "fake", "අසත්‍ය"]))
        true_count = sum(1 for r in significant_results if any(x in r["verdict"].lower() for x in ["true", "real", "සත්‍ය"]))

        if false_count > true_count:
            return "Likely FALSE", round(false_count / len(significant_results), 4)
        
        return "UNCERTAIN", 0.5

    def _scrape_online_news(self, claim: str, debug: bool = False):
        """Scrapes online news via SerpApi if no match is found in CSV."""
        if not self.serpapi_key or self.serpapi_key == "YOUR_SERP_API_KEY_HERE":
            print(f"DEBUG: [SM] ⚠️ SerpApi key not configured or placeholder used. Key found: '{self.serpapi_key[:5]}...'")
            return []
        lang = detect_language_safe(claim)

        # Build multiple query variants to improve match probability
        queries = [claim]
        if lang == "ta":
            if "tamil" not in claim.lower():
                queries.append(claim + " news tamil")
        if lang == "si":
            if "sinhala" not in claim.lower():
                queries.append(claim + " news sinhala")

        # shorter phrase (first 6 words) to broaden search
        try:
            words = claim.split()
            if len(words) > 6:
                queries.append(" ".join(words[:6]))
        except:
            pass

        # Try a basic ASCII transliteration if available (helps some APIs)
        try:
            from unidecode import unidecode
            ascii_q = unidecode(claim)
            if ascii_q and ascii_q != claim:
                queries.append(ascii_q)
        except Exception:
            # unidecode not installed — silently skip
            pass

        # Deduplicate while preserving order
        seen_q = set()
        final_queries = []
        for q in queries:
            q_str = (q or "").strip()
            if q_str and q_str not in seen_q:
                final_queries.append(q_str)
                seen_q.add(q_str)

        print(f"DEBUG: [SM] 🔍 SerpApi will try queries: {final_queries}")

        online_neighbors = []
        serpapi_dumps = []
        candidates_debug = []
        emb_claim = self.model.encode([claim], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(emb_claim)

        try:
            for search_query in final_queries:
                print(f"DEBUG: [SM] 🔍 Searching online for: {search_query} (Orig: {claim})")
                params = {
                    "q": search_query,
                    "tbm": "nws",
                    "api_key": self.serpapi_key,
                    "num": 10,
                    "gl": "lk" if lang in ["ta", "si"] else "us"
                }

                response = requests.get("https://serpapi.com/search", params=params, timeout=20)
                print(f"DEBUG: [SM] SerpApi response status: {response.status_code}")

                if response.status_code != 200:
                    print(f"DEBUG: [SM] ⚠️ SerpApi failed with status {response.status_code}. Response: {response.text[:200]}")
                    continue

                data = response.json()
                if debug:
                    serpapi_dumps.append({"query": search_query, "status": response.status_code, "keys": list(data.keys()) if isinstance(data, dict) else [], "raw": data})
                # Log small summary of response so we can debug empty results
                try:
                    print(f"DEBUG: [SM] SerpApi keys: {list(data.keys())}")
                except Exception:
                    pass

                # Collect candidate items from multiple fields
                candidates = []
                # news_results for news engine
                for item in data.get("news_results", []) or []:
                    candidates.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("source", "Online News")
                    })

                # top_stories or organic_results may contain news-like items
                for field in ("top_stories", "organic_results", "news_results"):
                    for item in data.get(field, []) or []:
                        # Some structures store headline under 'title' or 'snippet'
                        title = item.get("title") or item.get("snippet") or item.get("headline") or ""
                        link = item.get("link") or item.get("url") or ""
                        snippet = item.get("snippet") or ""
                        source = item.get("source") or item.get("domain") or item.get("displayed_link") or "Online News"
                        if title:
                            candidates.append({"title": title, "link": link, "snippet": snippet, "source": source})

                # Remove duplicates by title
                unique_seen = set()
                filtered = []
                for c in candidates:
                    t = (c.get("title", "") or "").strip()
                    if not t or t in unique_seen:
                        continue
                    unique_seen.add(t)
                    filtered.append(c)

                print(f"DEBUG: [SM] Found {len(filtered)} candidate items for query '{search_query}'")
                if debug:
                    candidates_debug.append({"query": search_query, "filtered_count": len(filtered), "titles": [ (c.get('title') or '')[:200] for c in filtered[:10] ]})

                # Score candidates
                for item in filtered:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    source = item.get("source", "Online News")
                    snippet = item.get("snippet", "")

                    emb_title = self.model.encode([title], convert_to_numpy=True).astype("float32")
                    faiss.normalize_L2(emb_title)
                    sim = float(np.dot(emb_claim, emb_title.T)[0][0])
                    print(f"DEBUG: [SM] Online match: '{title[:50]}...' Similarity: {sim:.4f}")

                    # Initialize best candidate values
                    best_sim = sim
                    best_text = title
                    used_fulltext = False

                    # Exact-match override on title (normalized)
                    try:
                        n_claim = self._normalize_text(claim)
                        n_title = self._normalize_text(title)
                        if n_claim and n_title and (n_claim in n_title or n_title in n_claim):
                            best_sim = 1.0
                            best_text = title
                            used_fulltext = False
                            print(f"DEBUG: [SM] Exact-match (title) override for '{title[:60]}...'")
                    except Exception:
                        pass

                    # First, if SerpApi provided a snippet, use it as a strong fallback
                    if best_sim < 0.7 and snippet:
                        try:
                            # Strip common leading location/site prefixes (e.g. "Colombo (News 1st) ")
                            try:
                                snippet_stripped = re.sub(r'^[^\u0B80-\u0BFF]+', '', snippet)
                            except Exception:
                                snippet_stripped = snippet

                            n_claim = self._normalize_text(claim)
                            n_snip = self._normalize_text(snippet_stripped)

                            # Token-overlap heuristic: if many claim tokens appear in snippet,
                            # treat as a near-exact match (handles prefixes like 'Colombo (News 1st)')
                            try:
                                claim_tokens = [t for t in (n_claim or "").split() if len(t) > 1]
                                snip_tokens = set((n_snip or "").split())
                                overlap = 0
                                if claim_tokens:
                                    overlap = sum(1 for t in claim_tokens if t in snip_tokens) / len(claim_tokens)
                                else:
                                    overlap = 0.0
                            except Exception:
                                overlap = 0.0

                            if overlap >= 0.6:
                                best_sim = 1.0
                                best_text = snippet
                                used_fulltext = False
                                print(f"DEBUG: [SM] Snippet token-overlap exact-match ({overlap:.2f}) for '{link}'")
                            elif n_claim and n_snip and (n_claim in n_snip or n_snip in n_claim):
                                best_sim = 1.0
                                best_text = snippet
                                used_fulltext = False
                                print(f"DEBUG: [SM] Exact-match (snippet) override for snippet from '{link}'")
                            else:
                                emb_snip = self.model.encode([snippet], convert_to_numpy=True).astype("float32")
                                faiss.normalize_L2(emb_snip)
                                snip_sim = float(np.dot(emb_claim, emb_snip.T)[0][0])
                                print(f"DEBUG: [SM] Snippet similarity for '{link}': {snip_sim:.4f}")
                                if snip_sim > best_sim:
                                    best_sim = snip_sim
                                    best_text = snippet
                                    used_fulltext = False
                        except Exception:
                            pass

                    # If still low similarity, try metadata headline first, then full article body
                    if best_sim < 0.7 and link:
                        # Try to extract a proper headline from page metadata (og:title, JSON-LD, h1)
                        try:
                            page_headline = self._fetch_headline_from_page(link)
                            if page_headline:
                                n_page_headline = self._normalize_text(page_headline)
                                try:
                                    if n_claim and n_page_headline and (n_claim in n_page_headline or n_page_headline in n_claim):
                                        best_sim = 1.0
                                        best_text = page_headline
                                        used_fulltext = False
                                        print(f"DEBUG: [SM] Exact-match (page headline) override for '{link}'")
                                    else:
                                        emb_head = self.model.encode([page_headline], convert_to_numpy=True).astype("float32")
                                        faiss.normalize_L2(emb_head)
                                        head_sim = float(np.dot(emb_claim, emb_head.T)[0][0])
                                        print(f"DEBUG: [SM] Page headline similarity for '{link}': {head_sim:.4f}")
                                        if head_sim > best_sim:
                                            best_sim = head_sim
                                            best_text = page_headline
                                            used_fulltext = False
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # If still low after headline, fall back to fetching full article body
                        if best_sim < 0.7:
                            try:
                                article_text = self._fetch_article_text(link)
                                if article_text and len(article_text.split()) > 20:
                                    # Try Indic normalization (best-effort)
                                    try:
                                        from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
                                        factory = IndicNormalizerFactory()
                                        normalizer = factory.get_normalizer("ta")
                                        article_text = normalizer.normalize(article_text)
                                    except Exception:
                                        pass

                                    # Exact-match override on body (normalized)
                                    try:
                                        n_body = self._normalize_text(article_text)
                                        if n_claim and n_body and n_claim in n_body:
                                            best_sim = 1.0
                                            best_text = article_text
                                            used_fulltext = True
                                            print(f"DEBUG: [SM] Exact-match (body) override for '{link}'")
                                        else:
                                            emb_body = self.model.encode([article_text], convert_to_numpy=True).astype("float32")
                                            faiss.normalize_L2(emb_body)
                                            body_sim = float(np.dot(emb_claim, emb_body.T)[0][0])
                                            print(f"DEBUG: [SM] Article body similarity for '{link}': {body_sim:.4f}")
                                            if body_sim > best_sim:
                                                best_sim = body_sim
                                                best_text = article_text
                                                used_fulltext = True
                                    except Exception:
                                        emb_body = self.model.encode([article_text], convert_to_numpy=True).astype("float32")
                                        faiss.normalize_L2(emb_body)
                                        body_sim = float(np.dot(emb_claim, emb_body.T)[0][0])
                                        print(f"DEBUG: [SM] Article body similarity for '{link}': {body_sim:.4f}")
                                        if body_sim > best_sim:
                                            best_sim = body_sim
                                            best_text = article_text
                                            used_fulltext = True
                            except Exception as e:
                                print(f"DEBUG: [SM] Article fetch/parse failed for {link}: {e}")

                    online_neighbors.append({
                        "similarity": best_sim,
                        "claim": title,
                        "title": title,
                        "headline": title,
                        "full_text_used": used_fulltext,
                        "text_sample": best_text[:400],
                        "verdict": "News Article",
                        "source": source,
                        "url": link,
                        "is_online": True
                    })

            # Keep best unique neighbors by url/title
            online_neighbors = sorted(online_neighbors, key=lambda x: x['similarity'], reverse=True)
            unique = []
            seen_keys = set()
            for n in online_neighbors:
                key = (n.get('url') or n.get('claim')).strip()
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                unique.append(n)
                if len(unique) >= 10:
                    break

            if debug:
                return unique, {
                    "serpapi": serpapi_dumps,
                    "candidates": candidates_debug
                }
            return unique
        except Exception as e:
            print(f"DEBUG: [SM] ⚠️ Online search error: {e}")
            import traceback
            traceback.print_exc()
            if debug:
                return [], {"serpapi": serpapi_dumps, "candidates": candidates_debug}
            return []

    def _fetch_article_text(self, url: str) -> str:
        """Fetches the article URL and tries to extract the main article text.

        Uses `newspaper3k` where available, otherwise falls back to readability + BeautifulSoup.
        """
        # Basic URL validation
        if not url or not url.startswith("http"):
            return ""

        try:
            # Try newspaper3k first
            try:
                from newspaper import Article
                art = Article(url)
                art.download()
                art.parse()
                text = art.text or ""
                if text and len(text.split()) > 20:
                    return text
            except Exception:
                # newspaper failed; fall back
                pass

            # Fallback: fetch and use readability
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return ""

            from readability import Document
            from bs4 import BeautifulSoup

            doc = Document(resp.text)
            article_html = doc.summary()
            if article_html:
                soup = BeautifulSoup(article_html, "html.parser")
                text = "\n".join(p.get_text(separator=" ") for p in soup.find_all("p"))
                if text and len(text.split()) > 20:
                    return text

            # Last resort: extract visible <p> from the full page
            soup = BeautifulSoup(resp.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(separator=" ") for p in paragraphs)
            return text or ""
        except Exception as e:
            print(f"DEBUG: [SM] _fetch_article_text error for {url}: {e}")
            return ""

    def _fetch_headline_from_page(self, url: str) -> str:
        """Fetch page and try to extract a proper headline from metadata or H1"""
        if not url or not url.startswith("http"):
            return ""
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return ""
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            # OG title
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                return og.get("content").strip()
            # twitter title
            tw = soup.find("meta", attrs={"name": "twitter:title"})
            if tw and tw.get("content"):
                return tw.get("content").strip()
            # meta title
            mt = soup.find("meta", attrs={"name": "title"})
            if mt and mt.get("content"):
                return mt.get("content").strip()
            # JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    import json
                    jd = json.loads(script.string or "{}")
                    if isinstance(jd, dict):
                        if jd.get("headline"):
                            return jd.get("headline").strip()
                        if jd.get("@graph"):
                            for node in jd.get("@graph", []):
                                if isinstance(node, dict) and node.get("headline"):
                                    return node.get("headline").strip()
                except Exception:
                    continue
            # h1 fallback
            h1 = soup.find("h1")
            if h1 and h1.get_text(strip=True):
                return h1.get_text(strip=True)
            return ""
        except Exception as e:
            print(f"DEBUG: [SM] _fetch_headline_from_page error for {url}: {e}")
            return ""

    def verify(self, claim: str, top_k: int = None, mode: str = "auto", debug: bool = False):
        """
        Verify a claim using local FAISS index and/or online SerpApi.

        mode: 'auto' (default) => use local and fallback to online when local best < 0.7
              'local' => only local FAISS search
              'online' => only online SerpApi search
              'both' => always query both and merge results
        """
        if top_k is None:
            top_k = self.top_k_default

        max_candidates = max(top_k * self.max_candidates_mult, top_k)

        lang = detect_language_safe(claim)
        requested_mode = (mode or "auto").lower()
        neighbors = []
        is_fallback = False

        # Local search
        if requested_mode in ("auto", "local", "both"):
            neighbors = self._semantic_search_unique(claim, top_k=top_k, max_candidates=max_candidates)

        # Online search only if requested or if auto fallback condition met
        online_neighbors = []
        debug_info = {}
        if requested_mode == "online":
            result_online = self._scrape_online_news(claim, debug=debug)
            if debug and isinstance(result_online, tuple):
                online_neighbors, dbg = result_online
                debug_info.update(dbg or {})
            else:
                online_neighbors = result_online
            is_fallback = True if online_neighbors else False
            neighbors = sorted(online_neighbors, key=lambda x: x['similarity'], reverse=True)[:top_k]

        elif requested_mode == "both":
            result_online = self._scrape_online_news(claim, debug=debug)
            if debug and isinstance(result_online, tuple):
                online_neighbors, dbg = result_online
                debug_info.update(dbg or {})
            else:
                online_neighbors = result_online
            if online_neighbors:
                is_fallback = True
            neighbors = sorted(online_neighbors + neighbors, key=lambda x: x['similarity'], reverse=True)[:top_k]

        elif requested_mode == "auto":
            # existing behavior: if best local < 0.7, try online and merge
            best_sim_csv = neighbors[0]['similarity'] if neighbors else 0
            print(f"DEBUG: [SM] Best CSV match similarity: {best_sim_csv:.4f}")
            if best_sim_csv < 0.7:
                print(f"DEBUG: [SM] Similarity {best_sim_csv:.4f} < 0.7. Triggering LIVE API search...")
                result_online = self._scrape_online_news(claim, debug=debug)
                if debug and isinstance(result_online, tuple):
                    online_neighbors, dbg = result_online
                    debug_info.update(dbg or {})
                else:
                    online_neighbors = result_online
                if online_neighbors:
                    print(f"DEBUG: [SM] Found {len(online_neighbors)} live results. Merging with local results.")
                    neighbors = sorted(online_neighbors + neighbors, key=lambda x: x['similarity'], reverse=True)[:top_k]
                    is_fallback = True
                else:
                    print("DEBUG: [SM] No live news results found or matched.")

        # Aggregate verdict
        final_verdict, confidence = self._aggregate_verdict(neighbors)

        # If Online Scraper found a match and aggregate didn't catch it
        if (is_fallback or (online_neighbors and requested_mode == "online")) and neighbors and neighbors[0].get('is_online'):
            best_sim = neighbors[0]['similarity']
            if best_sim > 0.5:
                final_verdict = "VERIFIED REAL (ONLINE)"
                confidence = best_sim

        result = {
            "input_claim": claim,
            "detected_language": lang,
            "requested_mode": requested_mode,
            "final_verdict": final_verdict,
            "confidence": float(confidence),
            "top_k": int(top_k),
            "neighbors": neighbors,
            "used_online_search": bool(is_fallback)
        }

        if debug:
            # Attach collected debug info: serpapi responses and candidate summaries
            # Some calls to _scrape_online_news may have filled debug_info already
            # If not, call _scrape_online_news once more with debug to collect diagnostics
            try:
                if not debug_info:
                    res = self._scrape_online_news(claim, debug=True)
                    if isinstance(res, tuple):
                        _, dbg = res
                        debug_info.update(dbg or {})
                # If debug_info was populated earlier, include it
            except Exception:
                pass

            # For safety, include placeholders if keys missing
            result["debug"] = debug_info

        return result
