# Modular PDF Processor API

A clean, modular FastAPI server for PDF processing with Document AI, DLP masking, RAG enhancement, Knowledge Graph construction, and test case generation.

## 🏗️ Project Structure

```
vertex_agent/
├── api_server_modular.py          # Main API server
├── modules/                       # Modular components
│   ├── document_ai.py            # PDF text extraction
│   ├── dlp_masking.py            # PII detection and masking
│   ├── rag_enhancement.py        # RAG corpus queries
│   ├── knowledge_graph.py        # KG construction and analysis
│   ├── test_generation.py        # AI-powered test case generation
│   └── mock_data_loader.py       # Mock data loading utilities
├── mockData/                      # Mock data directory
│   ├── documents/                # Sample PDF files
│   ├── responses/                # Mock API responses
│   ├── inputs/                   # Sample input data
│   └── configs/                  # Mock configuration files
├── requirements.txt              # Python dependencies
├── Dockerfile                   # Container configuration
└── venv/                          # Virtual environment
```

## 🚀 Quick Start

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Start the server:**
   ```bash
   python api_server_modular.py
   ```

3. **Test the API:**
   ```bash
   curl -X POST "http://localhost:8080/generate-ui-tests?gdpr_mode=true" \
        -F "file=@documents/PRD-3.pdf" \
        -H "Content-Type: multipart/form-data"
   ```

## 📡 API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /extract-document` - Document AI extraction only (PDF → structured text + entities)
- `POST /extract-mask` - Document AI + DLP masking (PDF → extraction + PII masking)
- `POST /rag-enhance` - Document AI + DLP + RAG enhancement (PDF → extraction + PII masking + RAG corpus)
- `POST /build-knowledge-graph` - Document AI + DLP + RAG + KG construction (PDF → knowledge graph with nodes & edges)
- `POST /generate-ui-tests` - Complete pipeline (Document AI → DLP → RAG → KG → Test Generation)

### Extract Document (Document AI Only)

Extract text and entities from a PDF using Google Cloud Document AI:

```bash
curl -X POST "http://localhost:8080/extract-document?use_mock=false" \
     -F "file=@mockData/documents/PRD-3.pdf" \
     -H "Content-Type: multipart/form-data"
```

### Extract + Mask (Document AI + DLP)

Extract text and automatically mask PII in one step:

```bash
curl -X POST "http://localhost:8080/extract-mask?gdpr_mode=true" \
     -F "file=@mockData/documents/PRD-3.pdf" \
     -H "Content-Type: multipart/form-data"
```

**Optimizations:**
- ✅ **Unified chunks**: Each chunk contains both `original_text` and `masked_text`
- ✅ **Non-blocking DLP**: Uses `asyncio.to_thread()` to prevent API blocking
- ✅ **Per-chunk edges**: `edges` array in each chunk for page-specific traceability
- ✅ **No duplication**: Single source of truth for `filename`, `mock_mode`, `gdpr_mode` (in `document`)
- ✅ **Flatter structure**: Per-chunk PII stats only (no global `total_pii_found` or `pii_types_detected`)
- ✅ **Smaller JSON**: Removed redundant fields, fully traceable from chunk-level data

### RAG Enhancement (Document AI + DLP + RAG)

Extract text, mask PII, and enhance with RAG corpus for compliance insights:

```bash
curl -X POST "http://localhost:8080/rag-enhance?gdpr_mode=true&rag_location=europe-west3" \
     -F "file=@mockData/documents/PRD-3.pdf" \
     -H "Content-Type: multipart/form-data"
```

**Parameters:**
- `rag_corpus_name` (str): Custom RAG corpus name (optional)
- `rag_location` (str): RAG corpus location (default: "europe-west3")

**Features:**
- ✅ **Async RAG Processing**: Concurrent chunk processing with `asyncio.gather()`
- ✅ **Dynamic Thresholding**: Intelligent similarity thresholds based on chunk length
- ✅ **Fuzzy Fallback**: Advanced fallback matching with `difflib.SequenceMatcher`
- ✅ **Policy Deduplication**: Smart deduplication of matched policies per chunk
- ✅ **Error Resilience**: Continues processing even if RAG corpus fails


### Build Knowledge Graph (Document AI + DLP + RAG + KG)

Extract text, mask PII, enhance with RAG, and build a comprehensive knowledge graph:

```bash
curl -X POST "http://localhost:8080/build-knowledge-graph?gdpr_mode=true&rag_location=europe-west3" \
     -F "file=@mockData/documents/PRD-3.pdf" \
     -H "Content-Type: multipart/form-data"
```

**Parameters:**
- `gdpr_mode` (bool): Enable PII masking with DLP (default: true)
- `rag_corpus_name` (str): Custom RAG corpus name (optional)
- `rag_location` (str): RAG corpus location (default: "europe-west3")
- `use_mock` (bool): Use mock data for testing (default: false)

**Features:**
- ✅ **Complete Pipeline**: Document AI → DLP → RAG → Knowledge Graph
- ✅ **Compliance Normalization**: Canonical IDs for compliance standards (GDPR:2016/679, CCPA:2018, etc.)
- ✅ **Dual Node Creation**: Creates compliance nodes from both `detected_compliance` and `relationships[]`
- ✅ **Comprehensive Metadata**: Graph density, avg confidence, compliance by type, top connected nodes
- ✅ **Direct Relationship Consumption**: Uses optimized `relationships[]` from chunks

**Use cases:**
- Visualize compliance traceability in graph databases (Neo4j, Memgraph)
- Analyze requirement coverage and gaps
- Export to graph visualization tools (Cytoscape, Gephi)
- Generate compliance reports with full traceability

### Generate UI Tests (Full Pipeline)

Run the complete compliance traceability pipeline:

```bash
curl -X POST "http://localhost:8080/generate-ui-tests?gdpr_mode=true" \
     -F "file=@mockData/documents/PRD-3.pdf" \
     -H "Content-Type: multipart/form-data"
```

## 🔧 Environment Variables

Set these environment variables for production:

- `PROJECT_ID` - **Google Cloud project ID (STRING, not project number!)**
  - ✅ Example: `"poc-genai-hacks"` or `"my-project-123"`
  - ❌ NOT the numeric project number like `"401328495550"`
  - 🔍 Find it: Go to [Google Cloud Console](https://console.cloud.google.com) → Project dropdown → "ID" column
- `LOCATION` - Document AI processor location (default: "us")
- `PROCESSOR_ID` - Document AI processor ID
- `RAG_CORPUS_NAME` - RAG corpus name
- `RAG_LOCATION` - RAG corpus location
- `GEMINI_LOCATION` - Gemini model location
- `USE_MOCK_DOCAI` - Set to "true" to use mock Document AI data (default: "false")

## 🔧 Document AI Setup

To use the actual Document AI API:

1. **Enable Document AI API** in your Google Cloud project
2. **Create a Document AI processor** in the Google Cloud Console
3. **Set environment variables:**
   ```bash
   # ⚠️ IMPORTANT: Use PROJECT ID (string), NOT project number (numeric)
   export PROJECT_ID="poc-genai-hacks"  # Your project ID (string like "my-project")
   export LOCATION="us"  # Processor location
   export PROCESSOR_ID="e7f52140009fdda2"  # Your processor ID
   ```

4. **Document AI Endpoint:**
   ```
   # Note: Document AI endpoints can use project number OR project ID
   https://us-documentai.googleapis.com/v1/projects/poc-genai-hacks/locations/us/processors/e7f52140009fdda2:process

   # However, DLP API REQUIRES project ID (string), NOT project number
   ```

5. **For testing with mock data:**
   ```bash
   # Use mock data for testing
   curl -X POST "http://localhost:8080/extract-document?use_mock=true" \
        -F "file=@mockData/documents/PRD-3.pdf"
   ```


**✅ Correct (Project ID):**
```bash
export PROJECT_ID="poc-genai-hacks"  # This is a project ID
```

## 📚 API Documentation

Visit `http://localhost:8080/docs` for interactive API documentation.
