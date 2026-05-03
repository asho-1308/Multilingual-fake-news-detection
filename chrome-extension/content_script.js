(function () {
  // Unicode checks for Tamil and Sinhala
  const isTamil = (s) => /[\u0B80-\u0BFF]/.test(s);
  const isSinhala = (s) => /[\u0D80-\u0DFF]/.test(s);
  const TAMIL_CLASSIFIER_URL = 'http://127.0.0.1:1000/predict';
  const SINHALA_CLASSIFIER_URL = 'http://127.0.0.1:2000/predict';
  const CANDIDATE_SELECTOR = 'h1,h2,h3,h4,h5,h6,[role="heading"],[class*="headline" i],[class*="title" i],[id*="headline" i],[id*="title" i],.article-title,.entry-title';

  // Create overlay element near an element
  function showOverlay(targetEl, contentHtml) {
    let overlay = targetEl._fakenews_overlay;
    if (!overlay) {
      const rect = targetEl.getBoundingClientRect();
      overlay = document.createElement('div');
      overlay.className = 'fnd-overlay';
      overlay.style.position = 'absolute';
      overlay.style.zIndex = 2147483647;
      overlay.style.left = `${window.scrollX + rect.right + 10}px`;
      overlay.style.top = `${window.scrollY + rect.top}px`;
      overlay.style.pointerEvents = 'auto';

      overlay.innerHTML = `
        <div class="fnd-box">
          <div class="fnd-close">×</div>
          <div class="fnd-content"></div>
        </div>
      `;

      document.body.appendChild(overlay);
      overlay.querySelector('.fnd-close').addEventListener('click', () => {
        overlay.remove();
        targetEl._fakenews_overlay = null;
      });
      targetEl._fakenews_overlay = overlay;
    }

    overlay.querySelector('.fnd-content').innerHTML = contentHtml;
    return overlay;
  }

  // Inject modern styles for overlays
  const style = document.createElement('style');
  style.textContent = `
    @keyframes fndFadeIn { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: translateX(0); } }
    .fnd-overlay { animation: fndFadeIn 0.3s ease-out; }
    .fnd-box {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      padding: 14px;
      border-radius: 10px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #1e293b;
      position: relative;
      min-width: 240px;
      max-width: 300px;
    }
    .fnd-close {
      position: absolute;
      right: 10px;
      top: 10px;
      cursor: pointer;
      font-size: 18px;
      color: #94a3b8;
      line-height: 1;
      transition: color 0.2s;
    }
    .fnd-close:hover { color: #475569; }
    .fnd-title { font-size: 11px; font-weight: 700; color: #64748b; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
    .fnd-result { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
    .fnd-prediction { font-size: 20px; font-weight: 800; letter-spacing: -0.01em; }
    .fnd-confidence { font-size: 12px; font-weight: 600; background: #f1f5f9; padding: 2px 8px; border-radius: 9999px; width: fit-content; }
    .fnd-details { font-size: 12px; color: #475569; border-top: 1px solid #f1f5f9; padding-top: 10px; display: flex; flex-direction: column; gap: 6px; }
    .fnd-detail-item { display: flex; align-items: flex-start; gap: 6px; }
    .fnd-detail-icon { font-size: 14px; }
    .fnd-real { color: #10b981; }
    .fnd-fake { color: #ef4444; }
    .fnd-loader { display: flex; align-items: center; gap: 10px; color: #64748b; font-size: 13px; font-weight: 500; }
    .fnd-spinner { width: 16px; height: 16px; border: 2px solid #e2e8f0; border-top-color: #2563eb; border-radius: 50%; animation: fndSpin 0.8s linear infinite; }
    @keyframes fndSpin { to { transform: rotate(360deg); } }
  `;
  document.head.appendChild(style);

  async function analyzeHeading(el, text) {
    // Sanitize text before sending: keep Tamil (\u0B80-\u0BFF), Sinhala (\u0D80-\u0DFF), common punctuation and spaces.
    // This avoids classifier OCR/cleaning returning empty strings for mixed/noisy headings.
    const sanitizeForBackend = (s) => {
      if (!s || typeof s !== 'string') return '';
      return s.replace(/[^\u0B80-\u0BFF\u0D80-\u0DFF\s\.,!\?"'\-:\;\(\)\/]/g, ' ').replace(/\s+/g, ' ').trim();
    };

    const sendText = sanitizeForBackend(text);
    const tamilText = isTamil(sendText || text);
    const sinhalaText = isSinhala(sendText || text);

    if (!tamilText && !sinhalaText) {
      showOverlay(el, `
        <div class="fnd-title">Language Not Supported</div>
        <div style="font-size:12px; color:#64748b; font-weight:500;">Only Tamil and Sinhala headings are analyzed.</div>
      `);
      return;
    }

    showOverlay(el, `
      <div class="fnd-loader">
        <div class="fnd-spinner"></div>
        <span>Analyzing content...</span>
      </div>
    `);

    try {
      const endpoint = tamilText ? TAMIL_CLASSIFIER_URL : SINHALA_CLASSIFIER_URL;
      const port = tamilText ? '1000' : '2000';
      const lang = tamilText ? 'Tamil' : 'Sinhala';
      
      // Retry logic with exponential backoff
      let lastErr = null;
      for (let attempt = 1; attempt <= 3; attempt++) {
        try {
          console.log(`DEBUG: Attempt ${attempt}/3 - Fetching from ${endpoint}`);
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 60000);
          
          const resp = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: sendText || text }),
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const data = await resp.json();
          console.log('DEBUG: Extension received data:', data);

          const pred = (data.prediction || data.label || 'Unknown').toString();
          const normalizedPred = pred.toLowerCase();
          const isFake = normalizedPred.includes('fake');
          const isReal = normalizedPred.includes('real') || normalizedPred.includes('credible');
          const colorClass = isFake ? 'fnd-fake' : (isReal ? 'fnd-real' : '');
          const confidenceValue = data.confidence != null ? data.confidence : 0;
          const confValue = (confidenceValue * 100).toFixed(0);

          const content = `
            <div class="fnd-title">Language-Specific Result</div>
            <div class="fnd-result">
              <div class="fnd-prediction ${colorClass}">${pred}</div>
              <div class="fnd-confidence">${confValue}% Final Confidence</div>
            </div>
            <div style="font-size:11px; color:#64748b; margin-top:8px">Used only the ${lang} classifier.</div>
          `;
          
          showOverlay(el, content);
          return; // Success!
        } catch (err) {
          lastErr = err;
          console.log(`DEBUG: Attempt ${attempt}/3 failed:`, err.message);
          if (attempt < 3) {
            await new Promise(r => setTimeout(r, Math.pow(2, attempt - 1) * 500)); // Backoff
          }
        }
      }
      throw lastErr || new Error('All retry attempts failed');
    } catch (err) {
      const port = tamilText ? '1000' : '2000';
      const lang = tamilText ? 'Tamil' : 'Sinhala';
      console.error('DEBUG: Final error:', err);
      console.error('DEBUG: Error message:', err?.message);
      console.error('DEBUG: Error name:', err?.name);
      showOverlay(el, `
        <div class="fnd-title">Service Error</div>
        <div style="font-size:12px; color:#ef4444; font-weight:500;">Connection failed to local backend</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">Ensure ${lang} classifier is running on port ${port}</div>
        <div style="font-size:10px; color:#cbd5e1; margin-top:4px; font-family: monospace;">Debug: ${err?.message || 'Unknown error'}</div>
      `);
    }
  }

  async function scanHeadings() {
    const all = Array.from(document.querySelectorAll(CANDIDATE_SELECTOR));
    const uniq = Array.from(new Set(all));
    const candidates = uniq.filter(el => {
      const t = (el.innerText || '').trim();
      if (!t || t.length < 4) return false;
      // ONLY analyze if the text contains Tamil or Sinhala characters
      if (isTamil(t) || isSinhala(t)) return true;
      return false; // Skip all other languages
    });

    const texts = candidates.map(e => (e.innerText || '').trim());

    // SEQUENTIAL EXECUTION: Wait for each heading to finish before starting the next
    for (const el of candidates) {
      const headingText = (el.innerText || '').trim();
      try {
        await analyzeHeading(el, headingText);
      } catch (err) {
        console.error('Error analyzing heading sequentially:', err);
      }
    }

    return { scanned: true, count: candidates.length, samples: texts.slice(0, 20) };
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg?.action === 'scan_headings') {
      scanHeadings().then(sendResponse).catch(() => sendResponse({ scanned: false }));
      return true;
    }
    if (msg?.action === 'analyze_heading' && msg.text) {
      const all = Array.from(document.querySelectorAll(CANDIDATE_SELECTOR));
      let el = all.find(e => (e.innerText || '').trim() === msg.text.trim());
      if (!el) el = all.find(e => (e.innerText || '').trim().includes(msg.text.trim().substring(0, 20)));
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
})();
