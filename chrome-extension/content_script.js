(function () {
  // Unicode checks for Tamil and Sinhala
  const isTamil = (s) => /[\u0B80-\u0BFF]/.test(s);
  const isSinhala = (s) => /[\u0D80-\u0DFF]/.test(s);

  // Create overlay element near an element
  function showOverlay(targetEl, text) {
    const existing = targetEl._fakenews_overlay;
    if (existing) return existing;

    const rect = targetEl.getBoundingClientRect();
    const overlay = document.createElement('div');
    overlay.className = 'fnd-overlay';
    overlay.style.position = 'absolute';
    overlay.style.zIndex = 2147483647;
    overlay.style.left = `${window.scrollX + rect.right - 8}px`;
    overlay.style.top = `${window.scrollY + rect.top}px`;
    overlay.style.maxWidth = '320px';
    overlay.style.pointerEvents = 'auto';

    overlay.innerHTML = `
      <div class="fnd-box">
        <div class="fnd-close">×</div>
        <div class="fnd-content">${text}</div>
      </div>
    `;

    document.body.appendChild(overlay);

    overlay.querySelector('.fnd-close').addEventListener('click', () => {
      overlay.remove();
      targetEl._fakenews_overlay = null;
    });

    targetEl._fakenews_overlay = overlay;
    return overlay;
  }

  // Send heading text to orchestrator and show result
  async function analyzeHeading(el, text) {
    try {
      const resp = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const data = await resp.json();
      const pred = data.final_prediction || 'Unknown';
      const conf = data.final_confidence != null ? (data.final_confidence * 100).toFixed(1) + '%' : '';
      const details = [];
      if (data.similarity && data.similarity.final_verdict) details.push(`Similarity: ${data.similarity.final_verdict}`);
      if (data.credibility && data.credibility.credibility) details.push(`Credibility: ${data.credibility.credibility}`);
      const content = `<strong>${pred}</strong> ${conf}<br/>${details.join('<br/>')}`;
      showOverlay(el, content);
    } catch (err) {
      showOverlay(el, `<strong>Error</strong><br/>${err.message}`);
    }
  }

  // Heuristic heading selector: h1-h6, role=heading, common classes and ids
  const CANDIDATE_SELECTOR = 'h1,h2,h3,h4,h5,h6,[role="heading"],[class*="headline" i],[class*="title" i],[id*="headline" i],[id*="title" i],.article-title,.entry-title';

  function getFontSizePx(el) {
    try {
      const fs = window.getComputedStyle(el).fontSize || '0px';
      return parseFloat(fs.replace('px', '')) || 0;
    } catch (e) {
      return 0;
    }
  }

  // Find headings using broader heuristics
  async function scanHeadings() {
    const all = Array.from(document.querySelectorAll(CANDIDATE_SELECTOR));
    const unique = Array.from(new Set(all));

    const candidates = unique.filter((el) => {
      const t = (el.innerText || '').trim();
      if (!t || t.length < 4) return false;

      // Accept if Tamil or Sinhala present
      if (isTamil(t) || isSinhala(t)) return true;

      // Accept if visually large (likely a heading)
      const fs = getFontSizePx(el);
      if (fs >= 18) return true;

      // Accept if class/id includes title/headline keywords
      const cls = (el.className || '') + ' ' + (el.id || '');
      if (/title|headline|heading/i.test(cls)) return true;

      return false;
    });

    const texts = candidates.map((el) => (el.innerText || '').trim());
    for (const el of candidates) {
      analyzeHeading(el, (el.innerText || '').trim());
    }

    return { count: candidates.length, samples: texts.slice(0, 10) };
  }

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.action === 'scan_headings') {
      scanHeadings()
        .then(({ count, samples }) => sendResponse({ scanned: true, count, samples }))
        .catch(() => sendResponse({ scanned: false }));
      return true; // will respond asynchronously
    }
    
    // Handle per-heading analyze request: msg.text
    if (msg && msg.action === 'analyze_heading' && typeof msg.text === 'string') {
      // find best matching element by exact or partial match
      const all = Array.from(document.querySelectorAll(CANDIDATE_SELECTOR));
      let el = all.find(e => (e.innerText || '').trim() === msg.text.trim());
      if (!el) el = all.find(e => (e.innerText || '').trim().includes(msg.text.trim().slice(0, 20)));
      if (!el && all.length) el = all[0];
      if (el) {
        analyzeHeading(el, (el.innerText || '').trim());
        sendResponse({ analyzed: true });
      } else {
        sendResponse({ analyzed: false });
      }
      return true;
    }
  });

  // Inject basic styles for overlays
  const style = document.createElement('style');
  style.textContent = `
  .fnd-overlay .fnd-box{background:rgba(255,255,255,0.98);border:1px solid #ddd;padding:8px;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,0.2);font-family:Arial, sans-serif;font-size:13px;color:#111}
  .fnd-overlay .fnd-close{position:absolute;right:6px;top:2px;cursor:pointer;font-weight:bold}
  .fnd-overlay .fnd-content{padding-right:10px}
  `;
  document.head.appendChild(style);
})();
