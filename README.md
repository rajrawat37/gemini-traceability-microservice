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
- `gdpr_mode` (bool): Enable PII masking with DLP (default: true)
- `rag_corpus_name` (str): Custom RAG corpus name (optional)
- `rag_location` (str): RAG corpus location (default: "europe-west3")

**Features:**
- ✅ **Async RAG Processing**: Concurrent chunk processing with `asyncio.gather()`
- ✅ **Dynamic Thresholding**: Intelligent similarity thresholds based on chunk length
- ✅ **Fuzzy Fallback**: Advanced fallback matching with `difflib.SequenceMatcher`
- ✅ **Policy Deduplication**: Smart deduplication of matched policies per chunk
- ✅ **Error Resilience**: Continues processing even if RAG corpus fails

**Response structure:**
```json
{
  "status": "success",
  "agent": "Document AI + DLP + RAG",
  "timestamp": "2025-01-25T14:30:22Z",
  "request_id": "uuid-here",
  "document": {
    "filename": "PRD-3.pdf",
    "mock_mode": false,
    "gdpr_mode": true,
    "rag_location": "europe-west3",
    "rag_corpus": "default"
  },
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "page_number": 1,
      "masked_text": "User email is [EMAIL_ADDRESS]",
      "original_text": "User email is john@example.com",
      "pii_found": true,
      "pii_count": 1,
      "pii_types": ["EMAIL_ADDRESS"],
      "embedding_ready_text": "user email is [email_address]",
      "relationships": [
        {
          "source_id": "req_001",
          "target_id": "GDPR:2016/679",
          "type": "REQUIRES",
          "target_class": "COMPLIANCE_STANDARD",
          "confidence": 0.8
        }
      ]
    }
  ],
  "context_docs": [
    {
      "chunk_id": "chunk_001",
      "text": "User email is [EMAIL_ADDRESS]",
      "matched_policies": [
        {
          "policy_name": "GDPR Data Protection",
          "policy_text": "EU data subject rights including consent, data minimization...",
          "similarity_score": 0.85,
          "source": "rag_corpus"
        }
      ],
      "source_type": "prd_document",
      "pii_found": true,
      "pii_types": ["EMAIL_ADDRESS"]
    }
  ],
  "summary": {
    "total_pages": 10,
    "total_chunks": 25,
    "requirements_found": 15,
    "compliance_standards_found": 8,
    "compliance_summary": ["GDPR:2016/679", "HIPAA:1996"],
    "pii_masking_performed": true,
    "chunks_with_pii": 8,
    "rag_enhancement": {
      "total_chunks_processed": 25,
      "total_policies_matched": 12,
      "chunks_with_policies": 8,
      "rag_corpus_used": "projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856",
      "rag_location": "europe-west3"
    },
    "total_context_docs": 25,
    "policies_matched": 12
  },
  "processor": {...}
}
```

**Key improvements:**
- `document`: Contains all document metadata once (no duplication across levels)
- `chunks[].pii_*`: Per-chunk PII details for granular control
- `summary.chunks_with_pii`: Aggregated count (calculate `total_pii_found` from chunks if needed)
- Smaller payload, easier to parse, fully traceable

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

**Response structure:**
```json
{
  "status": "success",
  "agent": "Knowledge Graph Builder",
  "timestamp": "2025-01-25T14:30:22Z",
  "request_id": "uuid-here",
  "document": {
    "filename": "PRD-3.pdf",
    "mock_mode": false,
    "gdpr_mode": true,
    "rag_location": "europe-west3",
    "rag_corpus": "default"
  },
  "knowledge_graph": {
    "nodes": [
      {
        "id": "REQ_001",
        "type": "REQUIREMENT",
        "title": "User data must be encrypted at rest",
        "text": "User data must be encrypted at rest using AES-256",
        "confidence": 0.85,
        "page_number": 1,
        "priority": "High"
      },
      {
        "id": "COMP_001",
        "type": "COMPLIANCE_STANDARD",
        "title": "GDPR:2016/679",
        "text": "General Data Protection Regulation",
        "confidence": 0.8,
        "source": "detected_compliance",
        "standard_type": "GDPR",
        "page_number": 1
      }
    ],
    "edges": [
      {
        "id": "EDGE_chunk_001_001",
        "from": "REQ_001",
        "to": "COMP_001",
        "relation": "REQUIRES_COMPLIANCE",
        "confidence": 0.75,
        "source": "chunk_relationships",
        "page": 1
      }
    ],
    "metadata": {
      "total_nodes": 30,
      "total_edges": 45,
      "requirement_nodes": 22,
      "compliance_nodes": 4,
      "test_case_nodes": 0,
      "graph_density": 1.5,
      "avg_confidence": 0.78,
      "cross_page_links": 7,
      "compliance_by_type": {
        "GDPR": 2,
        "CCPA": 1,
        "HIPAA": 1
      },
      "edges_by_relation": {
        "REQUIRES_COMPLIANCE": 40,
        "RELATED": 5
      },
      "top_connected_nodes": [
        {"node_id": "COMP_001", "connections": 15},
        {"node_id": "REQ_005", "connections": 8}
      ],
      "normalized_compliance_count": 4
    }
  },
  "pipeline_summary": {
    "docai": {
      "status": "success",
      "chunks_extracted": 25,
      "pages_processed": 7
    },
    "dlp": {
      "status": "success",
      "pii_masking_performed": true,
      "chunks_with_pii": 2
    },
    "rag": {
      "status": "success",
      "policies_matched": 11,
      "chunks_with_policies": 8
    },
    "kg": {
      "status": "success",
      "total_nodes": 30,
      "total_edges": 45,
      "graph_density": 1.5
    }
  }
}
```

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

## 🐛 Troubleshooting

### DLP Error: "400 Malformed parent field"

This error means you're using a **project number** instead of **project ID**.

**❌ Wrong (Project Number):**
```bash
export PROJECT_ID="401328495550"  # This is a project NUMBER
```

**✅ Correct (Project ID):**
```bash
export PROJECT_ID="poc-genai-hacks"  # This is a project ID
```

**How to find your project ID:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top of the page
3. You'll see 3 columns: **Name**, **ID**, and **Number**
4. Copy the value from the **ID** column (this is your project ID)
5. Use that value for `PROJECT_ID` environment variable

**Why this matters:**
- Document AI API accepts both project ID and project number
- **DLP API ONLY accepts project ID** (the string value, not numeric)

## 📚 API Documentation

Visit `http://localhost:8080/docs` for interactive API documentation.
