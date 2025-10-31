# Use Python 3.11 slim image for better compatibility
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Add /app to PYTHONPATH so modules can be imported
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api_server_modular.py ./
COPY modules ./modules
COPY mockData ./mockData

# Set environment variables
ENV PROJECT_ID=poc-genai-hacks
ENV LOCATION=us
ENV PROCESSOR_ID=e7f52140009fdda2
ENV RAG_CORPUS_NAME=projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856
ENV RAG_LOCATION=europe-west3
ENV GEMINI_LOCATION=us-central1
ENV GEMINI_MODEL=gemini-2.0-flash-001
ENV DLP_LOCATION=us

# Context expansion configuration (NEW!)
ENV ENABLE_CONTEXT_EXPANSION=true
ENV MAX_EXPANSION_SENTENCES=3
ENV MAX_EXPANSION_CHARS=300

# Note: PORT is set by Cloud Run automatically (defaults to 8080)
# Expose port
EXPOSE 8080

# Run the FastAPI server
# Cloud Run sets PORT env var automatically, default to 8080 if not set
CMD exec uvicorn api_server_modular:app --host 0.0.0.0 --port ${PORT:-8080}

