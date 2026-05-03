Chrome extension for Multilingual Fake News Detector

How it works
- Click the extension icon and press "Scan H1/H2 Headings".
- The content script scans H1 and H2 elements containing Tamil or Sinhala characters.
- For each heading found, it POSTs directly to the matching language classifier:
	- Tamil: `http://127.0.0.1:1000/predict`
	- Sinhala: `http://127.0.0.1:2000/predict`
- The overlay shows only the predicted label and confidence.

Install locally
1. Open Chrome and go to `chrome://extensions`.
2. Enable "Developer mode".
3. Click "Load unpacked" and select this `chrome-extension` folder.

Notes
- The Tamil and Sinhala classifier services must be running and accessible on ports `1000` and `2000`.
- This is an MVP; consider adding consent prompts, rate limiting, and batching for production.
