# Use the common base image
FROM multilingual-fake-news-detection-base:latest

# Install additional dependencies specific to orchestrator
RUN pip install --no-cache-dir langdetect==1.0.9

# Copy application code
COPY . .

# Expose port 5000
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "app.py"]