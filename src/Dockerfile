# Dockerfile — Base image for OCR invoice pipeline
FROM python:3.10-slim

# Install OS-level dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire app code into the container
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python", "ocr_worker.py"]
