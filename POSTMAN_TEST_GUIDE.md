# 📮 Postman Testing Guide - Traceability Fix Verification

## 🎯 Quick Start

### Base URL:
```
https://vertex-agent-api-lhvgyyfwuq-uc.a.run.app
```

### Latest Revision:
```
vertex-agent-api-00006-nb2 (Traceability Fix Deployed)
```

---

## ✅ Step 1: Health Check

**Method:** GET
**URL:** `{{base_url}}/health`

**Expected Response (200 OK):**
```json
{
    "status": "healthy",
    "service": "pdf-processor-with-kg-and-test-gen",
    "pipeline": "Document AI → DLP → RAG → Knowledge Graph → Test Generation",
    "version": "3.0.0"
}
```

---

## 🧪 Step 2: Test Traceability Fix

**Method:** POST
**URL:** `{{base_url}}/generate-ui-tests?gdpr_mode=true`

**Headers:**
- Content-Type: `multipart/form-data` (auto-set by Postman)

**Body (form-data):**
- Key: `file`
- Type: `File`
- Value: Select your PRD PDF (e.g., PRD-7.pdf)

**Expected Response Time:** 25-40 seconds

---

## 🔍 Step 3: Verify Traceability in Response

### What to Check:

#### 1. Test Cases Array
```json
{
  "status": "success",
  "test_categories": [
    {
      "category_name": "Security Tests",
      "test_cases": [...]
    }
  ]
}
```

#### 2. Individual Test Case Structure
```json
{
  "test_id": "TC_001",
  "title": "Verify AI-driven assistance is HIPAA compliant",
  "derived_from": "REQ-001",
  "traceability": {
    "requirement_id": "REQ-001",  // ✅ Should match derived_from
    "requirement_text": "Al-driven assistance: With the increasing availability...",  // ✅ Should be from page 1
    "pdf_locations": [
      {
        "page_number": 1,  // ✅ Should match requirement's actual page
        "chunk_id": "kg_node_REQ-001"
      }
    ],
    "kg_mapping": {
      "kg_nodes": [
        {
          "id": "REQ-001",  // ✅ Should match test's derived_from
          "type": "REQUIREMENT",
          "text": "Al-driven assistance: With the increasing availability...",  // ✅ Full requirement text
          "confidence": 0.85
        }
      ]
    }
  }
}
```

---

## ✅ Verification Checklist

### For Each Test Case, Verify:

- [ ] **`derived_from`** field exists (e.g., "REQ-001", "REQ-002")
- [ ] **`traceability.requirement_id`** matches `derived_from`
- [ ] **`traceability.requirement_text`** is NOT empty
- [ ] **`traceability.requirement_text`** matches the expected requirement from the PDF
- [ ] **`traceability.pdf_locations[0].page_number`** is correct
- [ ] **`traceability.kg_mapping.kg_nodes`** is NOT empty
- [ ] **`traceability.kg_mapping.kg_nodes[0].id`** matches `derived_from`

### Expected Results by Test Case:

| Test Case | Derived From | Expected Requirement Text (First 50 chars) | Expected Page |
|-----------|--------------|---------------------------------------------|---------------|
| TC_001    | REQ-001      | "Al-driven assistance: With the increasing..." | 1 |
| TC_002    | REQ-002      | "Text Paste: Users can directly paste..." | 2 |
| TC_003    | REQ-003      | "Clarity & Readability: Use text analysis..." | 2 |
| TC_004    | REQ-004      | "Quality Optimization: The system will..." | 3 |
| TC_005    | REQ-005      | "Context Awareness: The system will maintain..." | 4 |

---

## ❌ What Was Wrong (Before Fix)

### Example of Incorrect Traceability:
```json
{
  "test_id": "TC_001",
  "derived_from": "REQ-001",
  "traceability": {
    "requirement_id": "REQ-001",
    "requirement_text": "Pricing Model: Will the Al-based PRD Reviewer...",  // ❌ This is from page 7!
    "pdf_locations": [
      {
        "page_number": 3  // ❌ Wrong page!
      }
    ]
  }
}
```

**Problem:** All test cases showed text from pages 3, 4, or 7 regardless of their `derived_from` ID.

---

## ✅ What's Fixed (After Fix)

### Example of Correct Traceability:
```json
{
  "test_id": "TC_001",
  "derived_from": "REQ-001",
  "traceability": {
    "requirement_id": "REQ-001",
    "requirement_text": "Al-driven assistance: With the increasing availability...",  // ✅ Correct text from page 1
    "pdf_locations": [
      {
        "page_number": 1,  // ✅ Correct page!
        "chunk_id": "kg_node_REQ-001"
      }
    ],
    "kg_mapping": {
      "kg_nodes": [
        {
          "id": "REQ-001",
          "type": "REQUIREMENT",
          "text": "Al-driven assistance: With the increasing availability...",
          "confidence": 0.85
        }
      ]
    }
  }
}
```

**Solution:** Test cases now use Knowledge Graph nodes as the authoritative source for requirement data.

---

## 🔍 Debugging Tips

### If Traceability Looks Wrong:

1. **Check the Logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=vertex-agent-api" --limit=30 --format="value(textPayload)" | grep "Built requirements map"
```

**Expected Log:**
```
✅ Built requirements map from KG nodes: 22 requirements
```

2. **Verify KG Output in Response:**
Look for the `knowledge_graph_output` section in the response:
```json
{
  "knowledge_graph_output": {
    "status": "success",
    "nodes": [
      {
        "id": "REQ-001",
        "type": "REQUIREMENT",
        "text": "Al-driven assistance: With the increasing availability...",
        "page_number": 1
      }
    ]
  }
}
```

3. **Check Statistics:**
```json
{
  "statistics": {
    "total_tests": 11,
    "requirements_covered": 22  // ✅ Should be > 0
  }
}
```

---

## 📊 Full Response Structure

```json
{
  "status": "success",
  "document_ai_output": { ... },
  "dlp_output": { ... },
  "rag_output": {
    "status": "success",
    "context_docs": [ ... ],
    "matched_policies": [ ... ]  // ✅ Should have 21 policies
  },
  "knowledge_graph_output": {
    "status": "success",
    "nodes": [ ... ],  // ✅ Should have ~50-60 nodes
    "edges": [ ... ]   // ✅ Should have relationships
  },
  "test_generation_output": {
    "status": "success",
    "test_cases": [ ... ],  // ✅ Should have 10-15 tests
    "metadata": {
      "total_tests": 11,
      "requirements_covered": 22,
      "kg_relationships_used": 45
    }
  },
  "test_categories": [
    {
      "category_name": "Security Tests",
      "category_icon": "🔒",
      "test_cases": [ ... ],  // ✅ Check traceability here
      "total_tests": 3
    }
  ],
  "compliance_dashboard": {
    "coverage_score": 36.7,
    "standards_tracked": 21,
    "gaps_identified": [ ... ]
  }
}
```

---

## 🚀 Success Indicators

### ✅ Your test is successful if:
1. Response returns 200 OK
2. `test_categories` has 5 categories (Security, Compliance, Functional, Integration, Performance)
3. Total test cases is 10-15 (not 5 fallback tests)
4. Each test case has:
   - Non-empty `traceability.requirement_text`
   - Matching `derived_from` and `traceability.requirement_id`
   - Valid `traceability.kg_mapping.kg_nodes[]`
5. `compliance_dashboard.standards_tracked` is 21
6. `knowledge_graph_output.nodes` has requirements with matching IDs

### ❌ Test failed if:
1. Response is 500 Internal Server Error
2. Only 5 test cases generated (fallback mode)
3. `traceability.requirement_text` is empty or generic
4. All test cases show the same requirement text
5. `traceability.kg_mapping.kg_nodes` is empty

---

## 🎯 Quick Command Line Test

```bash
# Save response to file
curl -X POST "https://vertex-agent-api-lhvgyyfwuq-uc.a.run.app/generate-ui-tests?gdpr_mode=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@PRD-7.pdf" \
  -o response.json

# Check test cases
cat response.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for category in data.get('test_categories', []):
    for test in category.get('test_cases', []):
        print(f\"Test: {test['test_id']}, Derived: {test['derived_from']}, Req Text: {test['traceability']['requirement_text'][:50]}...\")
"

# Expected output:
# Test: TC_001, Derived: REQ-001, Req Text: Al-driven assistance: With the increasing availa...
# Test: TC_002, Derived: REQ-002, Req Text: Text Paste: Users can directly paste text from...
```

---

## 📞 Support

If you encounter issues, check:
1. **Service Logs:** https://console.cloud.google.com/logs/query?project=poc-genai-hacks&query=resource.type%3D%22cloud_run_revision%22%20resource.labels.service_name%3D%22vertex-agent-api%22
2. **Cloud Console:** https://console.cloud.google.com/run/detail/us-central1/vertex-agent-api?project=poc-genai-hacks
3. **API Docs:** https://vertex-agent-api-lhvgyyfwuq-uc.a.run.app/docs

**Your API is ready for testing! 🚀**
