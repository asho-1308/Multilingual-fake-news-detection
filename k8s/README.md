# Docker and Kubernetes Deployment for Multilingual Fake News Detection Backend

This guide explains how to build Docker images and deploy the backend services using Kubernetes.

## Services

- **tamil-classifier**: Runs on port 1000
- **sinhala-classifier**: Runs on port 2000
- **similarity-matcher**: Runs on port 3000
- **credibility-predictor**: Runs on port 4000
- **orchestrator**: Runs on port 5000

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
```

### Check Deployment

```bash
kubectl get pods
kubectl get services
```

### Access Services

The services are exposed as ClusterIP. To access them externally, you may need to create Ingress or use port-forwarding:

```bash
kubectl port-forward svc/tamil-classifier-service 1000:1000
kubectl port-forward svc/sinhala-classifier-service 2000:2000
kubectl port-forward svc/similarity-matcher-service 3000:3000
kubectl port-forward svc/credibility-predictor-service 4000:4000
kubectl port-forward svc/orchestrator-service 5000:5000
```

## Orchestrator

The orchestrator service is the main API that coordinates calls to the individual classifiers and predictors. It detects the language of the input text and routes it to the appropriate classifier, then checks for similarity and credibility. When the orchestrator runs, all microservices are available and running.