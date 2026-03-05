const scanBtn = document.getElementById("scanBtn");
const status = document.getElementById("status");
const summary = document.getElementById("summary");
const headingsList = document.getElementById("headingsList");

function clearList() {
  headingsList.innerHTML = "";
}

function addListItem(text, index) {
  const li = document.createElement("li");
  
  const span = document.createElement("div");
  span.className = "heading-text";
  span.textContent = text.length > 150 ? text.slice(0, 150) + "…" : text;
  span.title = text;
  
  const btn = document.createElement("button");
  btn.className = "analyze-btn";
  btn.textContent = "Analyze Content";
  
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Analyzing...";
    status.textContent = "Analyzing heading...";
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, { action: "analyze_heading", text }, (resp) => {
      btn.disabled = false;
      btn.textContent = "Analyze Content";
      
      if (!chrome.runtime.lastError && resp && resp.analyzed) {
        status.textContent = "Analysis result shown on page";
        return;
      }

      // Fallback
      const fn = (headingText) => {
        const sanitizeForBackend = (s) => (s || "").replace(/[^\u0B80-\u0BFF\u0D80-\u0DFF\s\.,!\?"'\-:\;\(\)\/]/g, " ").replace(/\s+/g, " ").trim();
        const payloadText = sanitizeForBackend(headingText) || headingText;
        return fetch("http://127.0.0.1:5000/predict", {
          method: "POST", 
          headers: { "Content-Type": "application/json" }, 
          body: JSON.stringify({ text: payloadText })
        }).then(r => r.json()).then(d => ({ ok: true, data: d })).catch(e => ({ ok: false, err: String(e) }));
      };

      chrome.scripting.executeScript({ target: { tabId: tab.id }, func: fn, args: [text] }, (res) => {
        if (!res || !res[0]) { status.textContent = "Analysis failed"; return; }
        const out = res[0].result;
        if (out && out.ok) {
          const d = out.data;
          const pred = d.final_prediction || "Unknown";
          const confValue = d.final_confidence != null ? (d.final_confidence * 100).toFixed(0) : "0";
          alert(`Result: ${pred} (${confValue}%)`);
          status.textContent = `Completed: ${pred}`;
        } else {
          status.textContent = "Connection Error";
        }
      });
    });
  });

  li.appendChild(span);
  li.appendChild(btn);
  headingsList.appendChild(li);
}

scanBtn.addEventListener("click", async () => {
  status.textContent = "Scanning and analyzing headlines...";
  clearList();
  summary.textContent = "";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    status.textContent = "No active tab";
    return;
  }

  // Request scan from content script - this triggers analyzeHeading on all elements in content_script.js
  chrome.tabs.sendMessage(tab.id, { action: "scan_headings" }, (response) => {
    if (!chrome.runtime.lastError && response && response.scanned) {
      status.textContent = "Popups appearing on news items";
      summary.textContent = `Analyzed ${response.count} headings`;
      const samples = response.samples || [];
      samples.forEach((s, i) => addListItem(s, i));
      return;
    }

    // Fallback: if content script not present
    if (chrome.runtime.lastError) {
        const fn = () => {
          const CANDIDATE_SELECTOR = "h1,h2,h3,h4,h5,h6,[role=\"heading\"],[class*=\"headline\" i],[class*=\"title\" i],[id*=\"headline\" i],[id*=\"title\" i],.article-title,.entry-title";
          const isTamil = (s) => /[\u0B80-\u0BFF]/.test(s);
          const isSinhala = (s) => /[\u0D80-\u0DFF]/.test(s);
          const all = Array.from(document.querySelectorAll(CANDIDATE_SELECTOR));
          const uniq = Array.from(new Set(all));
          const candidates = uniq.filter(el => {
            const t = (el.innerText || "").trim();
            return t.length > 5 && (isTamil(t) || isSinhala(t));
          });
          const texts = candidates.map(e => (e.innerText || "").trim()).slice(0, 20);
          return { count: candidates.length, samples: texts };
        };

        chrome.scripting.executeScript({ target: { tabId: tab.id }, func: fn }, (injectionResults) => {
          if (!injectionResults || !injectionResults[0] || !injectionResults[0].result) {
            status.textContent = "Scan failed";
            return;
          }
          const { count, samples } = injectionResults[0].result;
          status.textContent = "Headings found via fallback scanner";
          summary.textContent = `Scanned ${count} items`;
          (samples || []).forEach((s, i) => addListItem(s, i));
        });
    } else {
      status.textContent = "No headlines detected";
    }
  });
});
