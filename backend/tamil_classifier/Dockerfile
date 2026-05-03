# Use the common base image
FROM multilingual-fake-news-detection-base:latest

# Install local requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only runtime app and model assets
COPY main.py ./
COPY my_tamil_fake_news_model/ my_tamil_fake_news_model/
COPY final_trained_model/ final_trained_model/
COPY indic_nlp_resources/ indic_nlp_resources/
COPY tessdata/ tessdata/

# Copy the Tesseract language data file
COPY tessdata/tam.traineddata /usr/share/tesseract-ocr/4.00/tessdata/tam.traineddata

# Expose port 1000
EXPOSE 1000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:1000/health || exit 1

# Run the application
CMD ["python", "main.py"]
