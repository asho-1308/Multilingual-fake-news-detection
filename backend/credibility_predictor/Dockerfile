# Use the common base image
FROM multilingual-fake-news-detection-base:latest

# All dependencies are already installed in the base image

# Copy application code
COPY . .

# Expose port 4000
EXPOSE 4000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:4000/health || exit 1

# Run the application
CMD ["python", "app.py"]