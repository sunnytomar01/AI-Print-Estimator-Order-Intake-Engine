# Canonical backend Dockerfile for ai-print-estimator
# Keep only this Dockerfile for building the backend image. Removed/marked duplicates to avoid confusion.
FROM python:3.11-slim

WORKDIR /app

# Install system deps needed for image OCR (tesseract) and building Pillow
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libjpeg-dev \
       zlib1g-dev \
       tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY ./app /app/app

# Install Python deps including multipart handling and image libs
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlmodel psycopg2-binary pdfminer.six requests python-multipart pillow pytesseract openai

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
