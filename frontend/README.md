This frontend is a Vite + React application that talks to the backend microservices through environment-based service URLs.

## Local Development

```bash
npm install
npm run dev
```

By default the app expects the backend services to be available on localhost:

- Orchestrator: http://127.0.0.1:5000
- Tamil classifier: http://127.0.0.1:1000
- Sinhala classifier: http://127.0.0.1:2000
- Similarity matcher: http://127.0.0.1:3000
- Credibility predictor: http://127.0.0.1:4000

## Production Build

The API URLs are baked into the static build, so set them before running npm run build:

```bash
VITE_ORCHESTRATOR_URL=https://api.example.com \
VITE_TAMIL_URL=https://api.example.com \
VITE_SINHALA_URL=https://api.example.com \
VITE_SIMILARITY_URL=https://api.example.com \
VITE_CREDIBILITY_URL=https://api.example.com \
npm run build
```

## Docker

The repository includes a multi-stage Dockerfile that builds the app and serves it with Nginx.

Example:

```bash
docker build \
	--build-arg VITE_ORCHESTRATOR_URL=https://api.example.com \
	--build-arg VITE_TAMIL_URL=https://api.example.com \
	--build-arg VITE_SINHALA_URL=https://api.example.com \
	--build-arg VITE_SIMILARITY_URL=https://api.example.com \
	--build-arg VITE_CREDIBILITY_URL=https://api.example.com \
	-t multilingual-fake-news-frontend ./frontend
```
