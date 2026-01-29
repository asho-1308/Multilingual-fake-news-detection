const scanBtn = document.getElementById('scanBtn');
const status = document.getElementById('status');
const summary = document.getElementById('summary');
const headingsList = document.getElementById('headingsList');

function clearList() {
  headingsList.innerHTML = '';
}

function addListItem(text, index) {
  const li = document.createElement('li');
  li.style.marginBottom = '6px';
  const span = document.createElement('span');
  span.textContent = text.length > 120 ? text.slice(0, 120) + '…' : text;
  span.title = text;
  span.style.display = 'inline-block';
  span.style.width = '170px';
  const btn = document.createElement('button');
  btn.textContent = 'Analyze';
  btn.style.marginLeft = '6px';
  btn.addEventListener('click', async () => {
    status.textContent = 'Analyzing...';
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    // Try messaging the content script first
    chrome.tabs.sendMessage(tab.id, { action: 'analyze_heading', text }, (resp) => {
      if (!chrome.runtime.lastError && resp && resp.analyzed) {
        status.textContent = 'Analysis triggered';
        return;
      }

      // Fallback: execute a small fetch in the page context to call the orchestrator directly
      const fn = (headingText) => {
        return fetch('http://localhost:5000/predict', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: headingText })
        }).then(r => r.json()).then(d => ({ ok: true, data: d })).catch(e => ({ ok: false, err: String(e) }));
      };

      chrome.scripting.executeScript({ target: { tabId: tab.id }, func: fn, args: [text] }, (res) => {
        if (!res || !res[0]) { status.textContent = 'Analysis failed (injection)'; return; }
        const out = res[0].result;
        if (out && out.ok) {
          const d = out.data;
          alert('Prediction: ' + (d.final_prediction || 'Unknown') + '\nConfidence: ' + (d.final_confidence || 0));
          status.textContent = 'Analysis (fallback) complete';
        } else {
          status.textContent = 'Analysis failed: ' + (out && out.err ? out.err : 'unknown');
        }
      });
    });
  });
  li.appendChild(span);
  li.appendChild(btn);
  headingsList.appendChild(li);
}

scanBtn.addEventListener('click', async () => {
  status.textContent = 'Scanning...';
  clearList();
  summary.textContent = '';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    status.textContent = 'No active tab';
    return;
  }

  chrome.tabs.sendMessage(tab.id, { action: 'scan_headings' }, (response) => {
    if (!chrome.runtime.lastError && response && response.scanned) {
      status.textContent = '';
      summary.textContent = `Scanned ${response.count} headings`;
      const samples = response.samples || [];
      samples.forEach((s, i) => addListItem(s, i));
      if (!samples.length) {
        const note = document.createElement('div');
        note.textContent = 'No sample headings returned (page may have more). Use Analyze on items you see.';
        headingsList.appendChild(note);
      }
      return;
    }

    // Fallback: if content script not present, inject a page-scanner function
    if (chrome.runtime.lastError) {
      const fn = () => {
        const CANDIDATE_SELECTOR = 'h1,h2,h3,h4,h5,h6,[role="heading"],[class*="headline" i],[class*="title" i],[id*="headline" i],[id*="title" i],.article-title,.entry-title';
        const isTamil = (s) => /[\u0B80-\u0BFF]/.test(s);
        const isSinhala = (s) => /[\u0D80-\u0DFF]/.test(s);
        function getFontSizePx(el) { try { return parseFloat(window.getComputedStyle(el).fontSize || '0px') || 0; } catch(e) { return 0; } }
        const all = Array.from(document.querySelectorAll(CANDIDATE_SELECTOR));
        const uniq = Array.from(new Set(all));
        const candidates = uniq.filter(el => {
          const t = (el.innerText || '').trim(); if (!t || t.length < 4) return false;
          if (isTamil(t) || isSinhala(t)) return true;
          if (getFontSizePx(el) >= 18) return true;
          const cls = (el.className || '') + ' ' + (el.id || ''); if (/title|headline|heading/i.test(cls)) return true;
          return false;
        });
        const texts = candidates.map(e => (e.innerText || '').trim()).slice(0, 20);
        return { count: candidates.length, samples: texts };
      };

      chrome.scripting.executeScript({ target: { tabId: tab.id }, func: fn }, (injectionResults) => {
        if (!injectionResults || !injectionResults[0] || !injectionResults[0].result) {
          status.textContent = '';
          summary.textContent = 'No headings scanned';
          return;
        }
        const { count, samples } = injectionResults[0].result;
        status.textContent = '';
        summary.textContent = `Scanned ${count} headings (fallback)`;
        (samples || []).forEach((s, i) => addListItem(s, i));
      });
    } else {
      status.textContent = '';
      summary.textContent = 'No headings scanned';
    }
  });
});
