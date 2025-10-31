# Traceability View - Quick Reference

## When User Clicks "View Traceability" on Test Case Card

### Input
- **Test Case ID**: e.g., `TC_005`
- **Test Case Object** (from the card): Contains `derived_from` field (e.g., `"REQ-005"`)

### Required Data from API Response

#### 1. Requirement Details (ID, Text, Page, Confidence)

**Primary Source**:
```javascript
// From: response.knowledge_graph.nodes[]
const reqNode = response.knowledge_graph.nodes.find(
  n => n.id === testCase.derived_from && n.type === "REQUIREMENT"
);

// Extract:
{
  id: reqNode.id,                    // "REQ-005"
  text: reqNode.text,                // "Full requirement text"
  page: reqNode.page_number,         // 1
  confidence: reqNode.confidence      // 0.9
}
```

**Alternative Source**:
```javascript
// From: response.compliance_dashboard.audit_report.traceability_matrix[]
const reqEntry = response.compliance_dashboard.audit_report.traceability_matrix.find(
  t => t.requirement_id === testCase.derived_from
);

// Extract:
{
  id: reqEntry.requirement_id,           // "REQ-005"
  text: reqEntry.requirement_full_text,  // "Full requirement text"
  page: reqEntry.page_number,            // 1
  confidence: reqEntry.confidence        // 0.9
}
```

---

#### 2. Linked Test Cases (All tests for this requirement)

**Recommended Source**:
```javascript
// From: response.compliance_dashboard.audit_report.traceability_matrix[]
const reqEntry = response.compliance_dashboard.audit_report.traceability_matrix.find(
  t => t.requirement_id === testCase.derived_from
);

const linkedTestCases = reqEntry.test_cases;
// Returns: [
//   { test_id: "TC_005", title: "...", category: "...", priority: "..." },
//   { test_id: "TC_006", title: "...", category: "...", priority: "..." }
// ]
```

**Alternative Source**:
```javascript
// From: response.flow_visualization.requirement_coverage[]
const reqCoverage = response.flow_visualization.requirement_coverage.find(
  r => r.requirement_id === testCase.derived_from
);

const linkedTestCases = reqCoverage.test_cases;
```

---

#### 3. Compliance Standards (All standards for this requirement)

**Recommended Source**:
```javascript
// From: response.compliance_dashboard.audit_report.traceability_matrix[]
const reqEntry = response.compliance_dashboard.audit_report.traceability_matrix.find(
  t => t.requirement_id === testCase.derived_from
);

const complianceStandards = reqEntry.compliance_standards;
// Returns: [
//   { standard_id: "GDPR:2016/679", standard_name: "GDPR:2016/679", standard_type: "GDPR" },
//   { standard_id: "HIPAA:45-CFR-164", standard_name: "HIPAA:45-CFR-164", standard_type: "HIPAA" },
//   { standard_id: "FDA:21-CFR-11", standard_name: "FDA:21-CFR-11", standard_type: "FDA" }
// ]
```

**Alternative Source**:
```javascript
// From: response.knowledge_graph.edges[] + response.knowledge_graph.nodes[]
const reqId = testCase.derived_from;

// Find edges from requirement to compliance standards
const complianceEdges = response.knowledge_graph.edges.filter(
  e => e.from === reqId && e.relation === "GOVERNED_BY"
);

// Get compliance standard nodes
const complianceStandards = complianceEdges.map(edge => {
  const stdNode = response.knowledge_graph.nodes.find(
    n => n.id === edge.to && n.type === "COMPLIANCE_STANDARD"
  );
  return {
    standard_id: stdNode.id,
    standard_name: stdNode.title,
    standard_type: stdNode.standard_type
  };
});
```

---

#### 4. Traceability Chain (Visual representation)

**Source**: `response.knowledge_graph.edges[]`

```javascript
const reqId = testCase.derived_from;
const testId = testCase.test_id;

// Step 1: REQ → TC edges (requirements verified by test cases)
const reqToTestEdges = response.knowledge_graph.edges.filter(
  e => e.from === reqId && 
       e.relation === "VERIFIED_BY"
);

// Step 2: TC → Compliance edges (test cases ensuring compliance)
const testToComplianceEdges = response.knowledge_graph.edges.filter(
  e => e.from === testId && 
       e.relation === "ENSURES_COMPLIANCE_WITH"
);

// Step 3: REQ → Compliance edges (requirements governed by standards)
const reqToComplianceEdges = response.knowledge_graph.edges.filter(
  e => e.from === reqId && 
       e.relation === "GOVERNED_BY"
);

// Build chain structure:
// REQ-005 → TC_005 → GDPR:2016/679
//         ↓
//       TC_006 → HIPAA:45-CFR-164
```

---

## Complete Example: Building the Traceability View

```javascript
function buildTraceabilityView(testCaseId, apiResponse) {
  // 1. Find the test case
  const testCase = apiResponse.test_suite.test_categories
    .flatMap(cat => cat.test_cases)
    .find(tc => tc.test_id === testCaseId);
  
  if (!testCase) return null;
  
  const requirementId = testCase.derived_from;
  
  // 2. Get requirement details (preferred: from traceability_matrix)
  const reqEntry = apiResponse.compliance_dashboard?.audit_report?.traceability_matrix
    ?.find(t => t.requirement_id === requirementId);
  
  if (!reqEntry) {
    // Fallback to knowledge_graph.nodes
    const reqNode = apiResponse.knowledge_graph.nodes.find(
      n => n.id === requirementId && n.type === "REQUIREMENT"
    );
    if (!reqNode) return null;
    
    // Build from nodes and edges
    const linkedTests = apiResponse.test_suite.test_categories
      .flatMap(cat => cat.test_cases)
      .filter(tc => tc.derived_from === requirementId)
      .map(tc => ({
        test_id: tc.test_id,
        title: tc.title
      }));
    
    const complianceEdges = apiResponse.knowledge_graph.edges.filter(
      e => e.from === requirementId && e.relation === "GOVERNED_BY"
    );
    
    const complianceStandards = complianceEdges.map(edge => {
      const stdNode = apiResponse.knowledge_graph.nodes.find(
        n => n.id === edge.to && n.type === "COMPLIANCE_STANDARD"
      );
      return {
        standard_id: stdNode?.id,
        standard_name: stdNode?.title,
        standard_type: stdNode?.standard_type
      };
    }).filter(Boolean);
    
    return {
      requirement: {
        id: reqNode.id,
        text: reqNode.text,
        page: reqNode.page_number,
        confidence: reqNode.confidence
      },
      linked_test_cases: linkedTests,
      compliance_standards: complianceStandards,
      traceability_chain: buildChain(requirementId, testCaseId, apiResponse.knowledge_graph)
    };
  }
  
  // 3. Use traceability_matrix (easiest path - has everything)
  return {
    requirement: {
      id: reqEntry.requirement_id,
      text: reqEntry.requirement_full_text,
      page: reqEntry.page_number,
      confidence: reqEntry.confidence
    },
    linked_test_cases: reqEntry.test_cases.map(tc => ({
      test_id: tc.test_id,
      title: tc.title,
      category: tc.category,
      priority: tc.priority
    })),
    compliance_standards: reqEntry.compliance_standards,
    traceability_chain: buildChain(requirementId, testCaseId, apiResponse.knowledge_graph)
  };
}

function buildChain(reqId, testId, knowledgeGraph) {
  // Build visual chain: REQ → TC → Compliance
  const chain = [];
  
  // Get all test cases for this requirement
  const testEdges = knowledgeGraph.edges.filter(
    e => e.from === reqId && e.relation === "VERIFIED_BY"
  );
  
  testEdges.forEach(testEdge => {
    const tcId = testEdge.to;
    
    // Get compliance standards for this test case
    const complianceEdges = knowledgeGraph.edges.filter(
      e => e.from === tcId && e.relation === "ENSURES_COMPLIANCE_WITH"
    );
    
    complianceEdges.forEach(compEdge => {
      const compNode = knowledgeGraph.nodes.find(
        n => n.id === compEdge.to && n.type === "COMPLIANCE_STANDARD"
      );
      
      if (compNode) {
        chain.push({
          requirement: reqId,
          test_case: tcId,
          compliance_standard: compNode.id,
          compliance_name: compNode.title
        });
      }
    });
  });
  
  return chain;
}
```

---

## Response Structure Summary

| Data Needed | Primary Location | Alternative Location |
|-------------|------------------|---------------------|
| **Requirement Details** | `compliance_dashboard.audit_report.traceability_matrix[].requirement_*` | `knowledge_graph.nodes[]` (type: REQUIREMENT) |
| **Linked Test Cases** | `compliance_dashboard.audit_report.traceability_matrix[].test_cases[]` | `flow_visualization.requirement_coverage[].test_cases[]` |
| **Compliance Standards** | `compliance_dashboard.audit_report.traceability_matrix[].compliance_standards[]` | `knowledge_graph.edges[]` + `knowledge_graph.nodes[]` |
| **Traceability Chain** | `knowledge_graph.edges[]` (build from relationships) | `flow_visualization.visualization_data.edges[]` |

---

## ⭐ Recommended Approach

**Use `compliance_dashboard.audit_report.traceability_matrix`** - It contains ALL the data you need in one structured format:

```javascript
const traceabilityData = apiResponse.compliance_dashboard.audit_report.traceability_matrix.find(
  t => t.requirement_id === testCase.derived_from
);

// This object contains:
// - requirement_id, requirement_text, requirement_full_text
// - page_number, confidence
// - test_cases[] (with test_id, title, category, priority)
// - compliance_standards[] (with standard_id, standard_name, standard_type)
```

Then use `knowledge_graph.edges` only for building the visual chain diagram.

