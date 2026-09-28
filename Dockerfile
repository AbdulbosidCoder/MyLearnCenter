# Stage 1: build the Mini App
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: API (serves the built Mini App too) and bot share one image
FROM python:3.11-slim
# Tesseract reads text on pictures (Uzbek Latin and Cyrillic, Russian, English).
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-uzb tesseract-ocr-uzb-cyrl tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-vision.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Local vision and search models (Florence-2, multilingual-e5-small). Build with
# --build-arg VISION=false for a small image without them; the app then uses OCR and word search only.
ARG VISION=true
RUN if [ "$VISION" = "true" ]; then \
      pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-vision.txt; \
    fi
# Downloaded models and uploaded pictures live in volumes, so a rebuild does not lose them.
ENV HF_HOME=/app/models MEDIA_DIR=/app/media
COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend/dist
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
