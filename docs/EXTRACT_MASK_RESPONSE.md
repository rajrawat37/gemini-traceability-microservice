# `/extract-mask` API Response Structure

## Overview

The `/extract-mask` endpoint returns a comprehensive response containing:
- Document metadata
- Extracted text chunks with PII masking
- Detected requirements and compliance standards
- Relationships between requirements and compliance
- Summary statistics

## Response Schema

```json
{
  "status": "success",
  "agent": "Document AI + DLP",
  "document": {...},
  "chunks": [...],
  "summary": {...},
  "processor": {...}
}
```

---

## 1. Document Object

Contains metadata about the processed document.

```json
{
  "name": "Ai Patient Prd.pdf",
  "id": "doc_20251031_154448",
  "processed_at": "2025-10-31T15:44:48+00:00",
  "filename": "Ai Patient Prd.pdf",
  "mock_mode": false,
  "gdpr_mode": true
}
```

**Fields:**
- `name`: Original filename
- `id`: Unique document ID (format: `doc_YYYYMMDD_HHMMSS`)
- `processed_at`: ISO timestamp of processing
- `filename`: Filename used during processing
- `mock_mode`: Whether mock data was used (`false` = real API)
- `gdpr_mode`: Whether PII masking was enabled

---

## 2. Chunks Array

Each chunk represents a section of extracted text from the PDF with complete traceability.

### Chunk Structure

```json
{
  "chunk_id": "chunk_001",
  "labels": ["SECURITY", "COMPLIANCE", "FUNCTIONAL_REQUIREMENT"],
  "page_number": 1,
  "text": "Full extracted text...",
  "confidence": 0.9557953000068664,
  "text_anchor": {
    "start": 0,
    "end": 1623
  },
  "bounding_box": {
    "x_min": 0.12571103870868683,
    "y_min": 0.1063736230134964,
    "x_max": 0.5585892796516418,
    "y_max": 0.14901098608970642
  },
  "detected_compliance": [...],
  "detected_requirements": [...],
  "source": "Ai Patient Prd.pdf",
  "masked_text": "Text with PII masked...",
  "pii_found": false,
  "pii_count": 0,
  "pii_types": [],
  "original_text": "Original text before masking...",
  "embedding_ready_text": "Normalized text for embeddings...",
  "node_id": "NODE_chunk_001",
  "relationships": [...]
}
```

### Chunk Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | string | Unique identifier (e.g., `chunk_001`) |
| `labels` | array | Categories: SECURITY, COMPLIANCE, FUNCTIONAL_REQUIREMENT, etc. |
| `page_number` | integer | PDF page number (1-indexed) |
| `text` | string | Full extracted text from this chunk |
| `confidence` | float | Extraction confidence score (0.0-1.0) |
| `text_anchor` | object | Character positions in full document |
| `bounding_box` | object | PDF coordinates (normalized 0-1) for visual highlighting |
| `detected_compliance` | array | Compliance standards found in this chunk |
| `detected_requirements` | array | Requirements detected in this chunk |
| `source` | string | Source document filename |
| `masked_text` | string | Text with PII masked (same as original if no PII) |
| `pii_found` | boolean | Whether PII was detected |
| `pii_count` | integer | Number of PII instances found |
| `pii_types` | array | Types of PII detected (EMAIL, PHONE, NAME, etc.) |
| `original_text` | string | Original text before any masking |
| `embedding_ready_text` | string | Lowercased, normalized text for vector embeddings |
| `node_id` | string | Knowledge graph node ID |
| `relationships` | array | Relationships to other entities |

---

## 3. Detected Requirements

Each chunk contains an array of detected requirements:

```json
{
  "id": "REQ-013",
  "text": "Each requirement follows the format REQ-[CATEGORY]-[NUMBER]...",
  "type": "MODAL_VERB",
  "confidence": 0.85,
  "bounding_box": {
    "x_min": 0.12741751968860626,
    "y_min": 0.8465933799743652,
    "x_max": 0.871444821357727,
    "y_max": 0.8734065890312195
  }
}
```

**Requirement Types:**
- `MODAL_VERB`: Requirements using "shall", "must", "should"
- `ACTION_VERB`: Action-oriented statements
- `BULLET_POINT`: Bulleted requirement items
- `SECTION_HEADER`: Section headers that may indicate requirements

---

## 4. Detected Compliance Standards

Each chunk contains compliance standards referenced:

```json
{
  "name": "GDPR",
  "canonical_id": "GDPR:2016/679"
}
```

**Common Standards:**
- `GDPR:2016/679` - General Data Protection Regulation
- `HIPAA:45-CFR-164` - Health Insurance Portability and Accountability Act
- `SOC2` - System and Organization Controls 2

---

## 5. Relationships Array

Each chunk contains relationships linking requirements to compliance standards:

```json
{
  "edge_id": "EDGE_chunk_001_001",
  "source_id": "REQ-001",
  "target_id": "GDPR:2016/679",
  "type": "REQUIRES_COMPLIANCE",
  "target_class": "COMPLIANCE_STANDARD",
  "confidence": 0.7,
  "page": 1
}
```

**Relationship Types:**
- `REQUIRES_COMPLIANCE`: Requirement requires compliance with a standard
- `GOVERNED_BY`: Requirement is governed by a regulation
- `VERIFIED_BY`: Requirement is verified by a test case
- `ENSURES_COMPLIANCE_WITH`: Test case ensures compliance

---

## 6. Summary Object

Aggregated statistics across all chunks:

```json
{
  "total_pages": 4,
  "total_chunks": 4,
  "requirements_found": 60,
  "compliance_standards_found": 6,
  "total_edges": 112,
  "kg_ready": true,
  "pii_masking_performed": true,
  "chunks_with_pii": 0
}
```

**Fields:**
- `total_pages`: Number of pages in PDF
- `total_chunks`: Number of text chunks extracted
- `requirements_found`: Total requirements detected
- `compliance_standards_found`: Unique compliance standards found
- `total_edges`: Total relationships created (for knowledge graph)
- `kg_ready`: Whether data is ready for knowledge graph construction
- `pii_masking_performed`: Whether DLP masking was executed
- `chunks_with_pii`: Number of chunks containing PII

---

## 7. Processor Object

Information about the Document AI processor used:

```json
{
  "name": "projects/poc-genai-hacks/locations/us/processors/e7f52140009fdda2",
  "project_id": "poc-genai-hacks",
  "location": "us",
  "processor_id": "e7f52140009fdda2",
  "endpoint": "https://us-documentai.googleapis.com/v1/..."
}
```

---

## Use Cases

### 1. Display Extracted Text

```javascript
response.chunks.forEach(chunk => {
  console.log(`Page ${chunk.page_number}:`);
  console.log(chunk.text);
  console.log(`Confidence: ${(chunk.confidence * 100).toFixed(1)}%`);
});
```

### 2. Show Requirements

```javascript
response.chunks.forEach(chunk => {
  chunk.detected_requirements.forEach(req => {
    console.log(`${req.id}: ${req.text}`);
    console.log(`Type: ${req.type}, Confidence: ${req.confidence}`);
  });
});
```

### 3. Show Compliance Standards

```javascript
const allStandards = new Set();
response.chunks.forEach(chunk => {
  chunk.detected_compliance.forEach(comp => {
    allStandards.add(comp.canonical_id);
  });
});
console.log('Compliance Standards:', Array.from(allStandards));
```

### 4. Build Traceability Map

```javascript
const traceabilityMap = {};
response.chunks.forEach(chunk => {
  chunk.relationships.forEach(rel => {
    if (!traceabilityMap[rel.source_id]) {
      traceabilityMap[rel.source_id] = [];
    }
    traceabilityMap[rel.source_id].push({
      compliance: rel.target_id,
      type: rel.type,
      confidence: rel.confidence
    });
  });
});
```

### 5. Check PII Status

```javascript
response.chunks.forEach(chunk => {
  if (chunk.pii_found) {
    console.log(`Chunk ${chunk.chunk_id} contains PII:`);
    console.log(`Types: ${chunk.pii_types.join(', ')}`);
    console.log(`Masked text: ${chunk.masked_text}`);
  }
});
```

### 6. Visual Highlighting (Using Bounding Boxes)

```javascript
// Use bounding_box coordinates to highlight text in PDF viewer
chunk.detected_requirements.forEach(req => {
  const bbox = req.bounding_box;
  // bbox values are normalized (0-1), convert to pixel coordinates
  const x = bbox.x_min * pdfWidth;
  const y = bbox.y_min * pdfHeight;
  const width = (bbox.x_max - bbox.x_min) * pdfWidth;
  const height = (bbox.y_max - bbox.y_min) * pdfHeight;
  
  // Draw highlight rectangle
  drawHighlight(x, y, width, height);
});
```

---

## Response Statistics Example

From your response:
- **4 pages** processed
- **4 chunks** extracted
- **60 requirements** detected
- **6 compliance standards** found
- **112 relationships** created (ready for knowledge graph)
- **0 chunks with PII** (no PII detected in this document)
- **GDPR masking enabled** (though no PII found)

---

## Next Steps

After getting this response, you can:

1. **Feed to Knowledge Graph**: Use `chunks` array to build knowledge graph
2. **Generate Test Cases**: Use requirements and relationships for test generation
3. **RAG Enhancement**: Use `embedding_ready_text` for vector embeddings
4. **Visual Highlighting**: Use `bounding_box` coordinates to highlight in PDF viewer
5. **Compliance Analysis**: Analyze `detected_compliance` and relationships

---

## Integration Flow

```
/extract-mask
  ↓
Response with chunks, requirements, compliance
  ↓
/build-knowledge-graph (uses chunks)
  ↓
/generate-ui-tests (uses KG + chunks)
  ↓
/get-traceability (uses test results)
```

---

## Key Data for Frontend

**For displaying in UI:**

1. **Chunk List View**: Show all chunks with page numbers
2. **Requirements List**: Extract and display all `detected_requirements`
3. **Compliance Standards**: Show unique `detected_compliance` values
4. **Relationships**: Visualize `relationships` array as graph
5. **PII Status**: Show `pii_found` and `pii_types` per chunk
6. **PDF Highlighting**: Use `bounding_box` to highlight in PDF viewer

---

## Sample Frontend Code

```javascript
// Display chunks
const displayChunks = (response) => {
  return response.chunks.map(chunk => ({
    id: chunk.chunk_id,
    page: chunk.page_number,
    text: chunk.text.substring(0, 200) + '...',
    requirements: chunk.detected_requirements.length,
    compliance: chunk.detected_compliance.map(c => c.name),
    hasPII: chunk.pii_found,
    confidence: (chunk.confidence * 100).toFixed(1) + '%'
  }));
};

// Get all unique requirements
const getAllRequirements = (response) => {
  const reqs = new Map();
  response.chunks.forEach(chunk => {
    chunk.detected_requirements.forEach(req => {
      reqs.set(req.id, {
        id: req.id,
        text: req.text,
        type: req.type,
        confidence: req.confidence,
        page: chunk.page_number,
        boundingBox: req.bounding_box
      });
    });
  });
  return Array.from(reqs.values());
};

// Get all relationships
const getAllRelationships = (response) => {
  return response.chunks.flatMap(chunk => 
    chunk.relationships.map(rel => ({
      from: rel.source_id,
      to: rel.target_id,
      type: rel.type,
      confidence: rel.confidence,
      page: rel.page
    }))
  );
};
```

---

## Summary

The `/extract-mask` response provides:
- ✅ Complete text extraction with page-level traceability
- ✅ Requirement detection with bounding boxes
- ✅ Compliance standard identification
- ✅ Relationship mapping (requirements → compliance)
- ✅ PII detection and masking status
- ✅ Ready-to-use data for knowledge graph construction

Use this response as the foundation for building knowledge graphs, generating test cases, and creating traceability visualizations.

