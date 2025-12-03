# Modular PDF Processor API

A clean, modular FastAPI server for PDF processing with Document AI, DLP masking, RAG enhancement, Knowledge Graph construction, and test case generation.

Frontend Repositry : https://github.com/Rahul-sinha84/hack-2-skill

## 🔧 Environment Variables

Set these environment variables for production:

- `PROJECT_ID` - **Google Cloud project ID (STRING, not project number!)**
  - ✅ Example: `"poc-genai-hacks"` or `"my-project-123"`
  - 🔍 Find it: Go to [Google Cloud Console](https://console.cloud.google.com) → Project dropdown → "ID" column
- `LOCATION` - Document AI processor location (default: "us")
- `PROCESSOR_ID` - Document AI processor ID
- `RAG_CORPUS_NAME` - RAG corpus name
- `RAG_LOCATION` - RAG corpus location
- `GEMINI_LOCATION` - Gemini model location
- `USE_MOCK_DOCAI` - Set to "true" to use mock Document AI data (default: "false")

## 📚 API Documentation

Visit `http://localhost:8080/docs` for interactive API documentation.
