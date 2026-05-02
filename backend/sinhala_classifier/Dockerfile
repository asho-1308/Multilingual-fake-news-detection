FROM multilingual-fake-news-detection-base:latest

# All dependencies are already installed in the base image

# Copy application code
COPY app/ app/
COPY models/ models/

EXPOSE 2000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2000"]
