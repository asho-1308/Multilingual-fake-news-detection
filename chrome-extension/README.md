Chrome extension for Multilingual Fake News Detector

How it works
- Click the extension icon and press "Scan H1/H2 Headings".
- The content script scans H1 and H2 elements containing Tamil or Sinhala characters.
- For each heading found, it POSTs to the local orchestrator at `http://localhost:5000/predict` and displays a small overlay with the result.

Install locally
1. Open Chrome and go to `chrome://extensions`.
2. Enable "Developer mode".
3. Click "Load unpacked" and select this `chrome-extension` folder.

Notes
- The orchestrator (backend) must be running and accessible at `http://localhost:5000`.
- The orchestrator must allow CORS (the current `backend/orchestrator/app.py` uses `CORS(..., origins='*')`).
- This is an MVP; consider adding consent prompts, rate limiting, and batching for production.
