#!/bin/bash
# Start the API server with virtual environment

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Secure PDF Processor API...${NC}"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Check if dependencies are installed
if [ ! -f "venv/bin/uvicorn" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    ./venv/bin/pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating template...${NC}"
    cat > .env << EOF
# GCP Configuration
PROJECT_ID=your-project-id
LOCATION=us
PROCESSOR_ID=your-processor-id

# DLP Configuration
DLP_LOCATION=us

# RAG Configuration
RAG_CORPUS_NAME=projects/your-project-id/locations/europe-west3/ragCorpora/your-corpus-id
RAG_LOCATION=europe-west3

# Gemini Configuration
GEMINI_MODEL=gemini-2.0-flash-001
GEMINI_LOCATION=us-central1
EOF
    echo -e "${RED}❌ Please configure .env file with your GCP credentials${NC}"
    echo -e "${YELLOW}   Edit .env and add your PROJECT_ID, PROCESSOR_ID, and RAG_CORPUS_NAME${NC}"
    exit 1
fi

# Start the server
echo -e "${GREEN}🌐 Starting API server on http://localhost:8080${NC}"
echo -e "${YELLOW}📚 API docs available at http://localhost:8080/docs${NC}"
echo -e "${YELLOW}Press CTRL+C to stop the server${NC}\n"

./venv/bin/python api_server_modular.py
