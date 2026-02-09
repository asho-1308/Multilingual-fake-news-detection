# Run the full backend using Docker Compose from any location
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Step 1: Building common base image..." -ForegroundColor Cyan
docker build -t multilingual-fake-news-detection-base:latest -f ./backend/base.Dockerfile ./backend

Write-Host "`nStep 2: Building and starting all backend services..." -ForegroundColor Cyan
docker compose up --build -d

Write-Host "`nBackend services are starting. Check logs with: docker compose logs -f" -ForegroundColor Green
Write-Host "Orchestrator: http://localhost:5000" -ForegroundColor White
Write-Host "Tamil Classifier: http://localhost:1000" -ForegroundColor White
Write-Host "Sinhala Classifier: http://localhost:2000" -ForegroundColor White
Write-Host "Similarity Matcher: http://localhost:3000" -ForegroundColor White
Write-Host "Credibility Predictor: http://localhost:4000" -ForegroundColor White
