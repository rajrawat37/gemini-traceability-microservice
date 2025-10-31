# Traceability View Data Requirements

## Overview
When a user clicks "View Traceability" on a **test case card**, the UI needs to display:

1. **Requirement Details**: ID, Text, Page, Confidence
2. **Traceability Chain**: Visual representation (REQ-005 → TC_005 → GDPR:2016/679)
3. **Linked Test Cases**: All test cases that verify the same requirement
4. **Compliance Standards**: All standards that govern the requirement

## Data Location in API Response

The `/generate-ui-tests` endpoint already returns all necessary data. Here's where to find each piece:

### 1. Requirement Details
**Location**: `response.knowledge_graph.nodes[]`

Find the requirement node matching the test case's `derived_from` field:

```json
{
  "id": "REQ-005",
  "type": "REQUIREMENT",
  "text": "Full requirement text here",
  "page_number": 1,
  "confidence": 0.9,
  "title": "REQ-005"
}
```

**Alternative Location**: `response.compliance_dashboard.audit_report.traceability_matrix[]`

This also contains requirement details but in a pre-computed format:
```json
{
  "requirement_id": "REQ-005",
  "requirement_text": "Full requirement text",
  "requirement_full_text": "Complete requirement text",
  "page_number": 1,
  "confidence": 0.9
}
```

### 2. Traceability Chain
**Location**: `response.knowledge_graph.edges[]`

To build the chain REQ-005 → TC_005 → GDPR:2016/679, you need to:

1. Find edges where `from == "REQ-005"` and `to == test_case_id` (relationship type: "VERIFIED_BY")
2. Find edges where `from == test_case_id` and `to == compliance_standard_id` (relationship type: "ENSURES_COMPLIANCE_WITH")
3. Find edges where `from == "REQ-005"` and `to == compliance_standard_id` (relationship type: "GOVERNED_BY")

**Example edge structure**:
```json
{
  "id": "edge_001",
  "from": "REQ-005",
  "to": "TC_005",
  "relation": "VERIFIED_BY",
  "confidence": 0.9
}
```

**Alternative Location**: `response.flow_visualization.requirement_coverage[]`

Pre-computed requirement coverage with test cases and compliance standards:
```json
{
  "requirement_id": "REQ-005",
  "requirement_text": "Full requirement text",
  "test_cases": [
    {
      "test_id": "TC_005",
      "title": "Test Title",
      "category": "Security Tests",
      "priority": "High"
    },
    {
      "test_id": "TC_006",
      "title": "Another Test",
      "category": "Compliance Tests",
      "priority": "Medium"
    }
  ],
  "compliance_standards": [
    "GDPR:2016/679",
    "HIPAA:45-CFR-164"
  ]
}
```

### 3. Linked Test Cases
**Location**: Multiple sources, most convenient:

**Option A**: `response.flow_visualization.requirement_coverage[].test_cases[]`
- Pre-computed list of all test cases for each requirement

**Option B**: `response.test_suite.test_categories[].test_cases[]`
- Filter where `derived_from == requirement_id`

**Option C**: `response.compliance_dashboard.audit_report.traceability_matrix[]`
- Each entry has a `test_cases[]` array

**Example structure**:
```json
[
  {
    "test_id": "TC_005",
    "title": "Test Case Title",
    "category": "Security Tests",
    "priority": "High"
  },
  {
    "test_id": "TC_006",
    "title": "Another Test Case",
    "category": "Compliance Tests",
    "priority": "Medium"
  }
]
```

### 4. Compliance Standards
**Location**: Multiple sources:

**Option A**: `response.knowledge_graph.nodes[]` + `response.knowledge_graph.edges[]`
- Find all edges where `from == requirement_id`
- Get compliance standard nodes where `type == "COMPLIANCE_STANDARD"`

**Option B**: `response.flow_visualization.requirement_coverage[].compliance_standards[]`
- Pre-computed list (but may only show names, not full details)

**Option C**: `response.compliance_dashboard.audit_report.traceability_matrix[].compliance_standards[]`
- Full compliance standard objects with IDs

**Example structure**:
```json
[
  {
    "standard_id": "GDPR:2016/679",
    "standard_name": "GDPR:2016/679",
    "standard_type": "GDPR"
  },
  {
    "standard_id": "HIPAA:45-CFR-164",
    "standard_name": "HIPAA:45-CFR-164",
    "standard_type": "HIPAA"
  },
  {
    "standard_id": "FDA:21-CFR-11",
    "standard_name": "FDA:21-CFR-11",
    "standard_type": "FDA"
  }
]
```

## Recommended Implementation

### Step 1: Get the Test Case
When user clicks "View Traceability" on test case `TC_005`:

```javascript
const testCase = findTestCase("TC_005"); // From test_suite.test_categories
const requirementId = testCase.derived_from; // "REQ-005"
```

### Step 2: Get Requirement Details
```javascript
const requirementNode = knowledgeGraph.nodes.find(
  n => n.id === requirementId && n.type === "REQUIREMENT"
);

const requirementDetails = {
  id: requirementNode.id,
  text: requirementNode.text,
  page: requirementNode.page_number,
  confidence: requirementNode.confidence
};
```

### Step 3: Get Linked Test Cases
```javascript
const requirementCoverage = flowVisualization.requirement_coverage.find(
  r => r.requirement_id === requirementId
);

const linkedTestCases = requirementCoverage.test_cases;
// Or search all test cases:
const linkedTestCases = testSuite.test_categories
  .flatMap(cat => cat.test_cases)
  .filter(tc => tc.derived_from === requirementId)
  .map(tc => ({
    test_id: tc.test_id,
    title: tc.title,
    category: tc.category,
    priority: tc.priority
  }));
```

### Step 4: Get Compliance Standards
```javascript
const complianceStandards = [];

// Get from requirement coverage (simplest)
if (requirementCoverage.compliance_standards) {
  // These are just names, need to find full details
  requirementCoverage.compliance_standards.forEach(stdName => {
    const stdNode = knowledgeGraph.nodes.find(
      n => n.type === "COMPLIANCE_STANDARD" && 
           (n.title === stdName || n.id === stdName)
    );
    if (stdNode) {
      complianceStandards.push({
        standard_id: stdNode.id,
        standard_name: stdNode.title,
        standard_type: stdNode.standard_type || "UNKNOWN"
      });
    }
  });
}

// OR get from traceability matrix (most complete)
const traceabilityEntry = auditReport.traceability_matrix.find(
  t => t.requirement_id === requirementId
);
const complianceStandards = traceabilityEntry.compliance_standards;
```

### Step 5: Build Traceability Chain
```javascript
const traceabilityChain = [];

// Find REQ → TC edges
const reqToTestEdges = knowledgeGraph.edges.filter(
  e => e.from === requirementId && 
       e.to === testCase.test_id &&
       e.relation === "VERIFIED_BY"
);

// Find TC → Compliance edges
const testToComplianceEdges = knowledgeGraph.edges.filter(
  e => e.from === testCase.test_id &&
       e.relation === "ENSURES_COMPLIANCE_WITH"
);

// Find REQ → Compliance edges
const reqToComplianceEdges = knowledgeGraph.edges.filter(
  e => e.from === requirementId &&
       e.relation === "GOVERNED_BY"
);

// Build chain representation
// REQ-005 → TC_005 → GDPR:2016/679
//         ↓
//       TC_006 → HIPAA:45-CFR-164
```

## Complete Response Structure Needed

For the "View Traceability" feature, you need access to:

```json
{
  "test_suite": {
    "test_categories": [
      {
        "test_cases": [
          {
            "test_id": "TC_005",
            "derived_from": "REQ-005",
            "traceability": {
              "requirement_id": "REQ-005",
              "requirement_text": "...",
              "pdf_locations": [...],
              "compliance_references": [...]
            }
          }
        ]
      }
    ]
  },
  "knowledge_graph": {
    "nodes": [
      {
        "id": "REQ-005",
        "type": "REQUIREMENT",
        "text": "Full requirement text",
        "page_number": 1,
        "confidence": 0.9
      },
      {
        "id": "GDPR:2016/679",
        "type": "COMPLIANCE_STANDARD",
        "title": "GDPR:2016/679",
        "standard_type": "GDPR"
      }
    ],
    "edges": [
      {
        "from": "REQ-005",
        "to": "TC_005",
        "relation": "VERIFIED_BY"
      },
      {
        "from": "TC_005",
        "to": "GDPR:2016/679",
        "relation": "ENSURES_COMPLIANCE_WITH"
      },
      {
        "from": "REQ-005",
        "to": "GDPR:2016/679",
        "relation": "GOVERNED_BY"
      }
    ]
  },
  "flow_visualization": {
    "requirement_coverage": [
      {
        "requirement_id": "REQ-005",
        "requirement_text": "Full requirement text",
        "test_cases": [...],
        "compliance_standards": ["GDPR:2016/679", "HIPAA:45-CFR-164"]
      }
    ]
  },
  "compliance_dashboard": {
    "audit_report": {
      "traceability_matrix": [
        {
          "requirement_id": "REQ-005",
          "requirement_text": "Full requirement text",
          "requirement_full_text": "Complete requirement text",
          "page_number": 1,
          "confidence": 0.9,
          "test_cases": [...],
          "compliance_standards": [...]
        }
      ]
    }
  }
}
```

## Summary

**Most Convenient Approach**: Use `compliance_dashboard.audit_report.traceability_matrix` - it already contains everything you need in one place:
- Requirement details (ID, text, page, confidence)
- Linked test cases (with IDs and titles)
- Compliance standards (with IDs and names)

**For Traceability Chain Visualization**: Use `knowledge_graph.edges` to build the visual chain representation.

**Fallback**: If traceability_matrix is not available, combine data from:
- `knowledge_graph.nodes` (requirements and compliance standards)
- `flow_visualization.requirement_coverage` (test cases and compliance links)
- `test_suite.test_categories` (test case details)

