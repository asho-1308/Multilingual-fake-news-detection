# Docker and Kubernetes Deployment for Multilingual Fake News Detection Backend

This guide explains how to build Docker images and deploy the backend services using Kubernetes.

## Services

- **tamil-classifier**: Runs on port 1000
- **sinhala-classifier**: Runs on port 2000
- **similarity-matcher**: Runs on port 3000
- **credibility-predictor**: Runs on port 4000
- **orchestrator**: Runs on port 5000
- **frontend**: Runs on port 80 inside the container and is typically exposed through Ingress or port-forwarding

## Building Docker Images

From the root directory of the project, run the following commands to build the images:

```bash
# Build Tamil Classifier
docker build -t tamil-classifier:latest ./backend/tamil_classifier

# Build Sinhala Classifier
docker build -t sinhala-classifier:latest ./backend/sinhala_classifier

# Build Similarity Matcher
docker build -t similarity-matcher:latest ./backend/similarity_matcher

# Build Credibility Predictor
docker build -t credibility-predictor:latest ./backend/credibility_predictor

# Build Orchestrator
docker build -t orchestrator:latest ./backend/orchestrator

# Build Frontend (replace URLs with your public deployment endpoints)
docker build \
	--build-arg VITE_ORCHESTRATOR_URL=https://api.example.com \
	--build-arg VITE_TAMIL_URL=https://api.example.com \
	--build-arg VITE_SINHALA_URL=https://api.example.com \
	--build-arg VITE_SIMILARITY_URL=https://api.example.com \
	--build-arg VITE_CREDIBILITY_URL=https://api.example.com \
	-t frontend:latest ./frontend
```

## Running with Docker Compose

To run all services locally using Docker Compose:

```bash
docker-compose up --build
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (e.g., Minikube, Kind, or cloud provider)
- kubectl configured

### Deploy Services

Apply the Kubernetes manifests:

```bash
kubectl apply -f k8s/
```

Or apply individually:

```bash
kubectl apply -f k8s/tamil-classifier.yaml
kubectl apply -f k8s/sinhala-classifier.yaml
kubectl apply -f k8s/similarity-matcher.yaml
kubectl apply -f k8s/credibility-predictor.yaml
kubectl apply -f k8s/orchestrator.yaml
kubectl apply -f k8s/frontend.yaml
```

### Check Deployment

```bash
kubectl get pods
kubectl get services
```

### Access Services

The backend services are exposed as ClusterIP. To access them externally, you may need to create Ingress or use port-forwarding. The frontend is usually the public entrypoint:

```bash
kubectl port-forward svc/frontend-service 8080:80
kubectl port-forward svc/tamil-classifier-service 1000:1000
kubectl port-forward svc/sinhala-classifier-service 2000:2000
kubectl port-forward svc/similarity-matcher-service 3000:3000
kubectl port-forward svc/credibility-predictor-service 4000:4000
kubectl port-forward svc/orchestrator-service 5000:5000
```

## Orchestrator

The orchestrator service is the main API that coordinates calls to the individual classifiers and predictors. It detects the language of the input text and routes it to the appropriate classifier, then checks for similarity and credibility. When the orchestrator runs, all microservices are available and running.

## Frontend Deployment Notes

The frontend is a Vite static build, so the API URLs are embedded at build time. For production deployments you should:

1. Build the frontend image with the production API URLs.
2. Publish the image to a registry.
3. Deploy the frontend alongside the backend services.
4. Put Ingress, a load balancer, or a reverse proxy in front of the frontend and API if you want a public URL.