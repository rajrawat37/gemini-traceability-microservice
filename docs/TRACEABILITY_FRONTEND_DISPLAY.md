# Traceability View - Frontend Display Format

## Response Structure

The `/get-traceability` endpoint returns structured data that should be displayed in a modal or detail panel. Here's how to format it for the frontend:

## UI Layout Structure

### 1. Requirement Details Section (Header)

```
┌─────────────────────────────────────────────────────────────┐
│  View Traceability: REQ-013                                 │
│                                                             │
│  Requirement Details                                        │
│  ────────────────────                                      │
│  ID: REQ-013                                                │
│  Text: Each requirement follows the format...              │
│  Page: 1 | Confidence: 85%                                 │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```jsx
<div className="requirement-header">
  <h2>View Traceability: {response.requirement.id}</h2>
  <div className="requirement-details">
    <div><strong>ID:</strong> {response.requirement.id}</div>
    <div><strong>Text:</strong> {response.requirement.text}</div>
    <div>
      <strong>Page:</strong> {response.requirement.page} | 
      <strong> Confidence:</strong> {(response.requirement.confidence * 100).toFixed(0)}%
    </div>
  </div>
</div>
```

---

### 2. Traceability Chain Visualization (Main Section)

```
┌─────────────────────────────────────────────────────────────┐
│  Traceability Chain                                         │
│  ────────────────────                                      │
│                                                             │
│  REQ-013                                                    │
│    ├─→ TC_005 → GDPR:2016/679                              │
│    ├─→ TC_005 → HIPAA:45-CFR-164                           │
│    ├─→ TC_013 → GDPR:2016/679                              │
│    ├─→ TC_013 → HIPAA:45-CFR-164                            │
│    ├─→ GDPR:2016/679 (direct)                              │
│    └─→ HIPAA:45-CFR-164 (direct)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```jsx
<div className="traceability-chain">
  <h3>Traceability Chain</h3>
  <div className="chain-visualization">
    {/* Requirement Node */}
    <div className="requirement-node">{response.requirement.id}</div>
    
    {/* Chain Paths */}
    {response.traceability_chain.map((chain, index) => (
      <div key={index} className="chain-path">
        {chain.test_case_id ? (
          <>
            <div className="arrow">↓</div>
            <div className="test-case-node">
              {chain.test_case_id}: {chain.test_case_title}
            </div>
            <div className="arrow">→</div>
            <div className="compliance-node">
              {chain.compliance_standard_name}
              {chain.inferred_from_data && <span className="badge">Inferred</span>}
            </div>
          </>
        ) : chain.direct_relationship ? (
          <>
            <div className="arrow">→</div>
            <div className="compliance-node">
              {chain.compliance_standard_name}
              <span className="badge direct">Direct</span>
            </div>
          </>
        ) : null}
      </div>
    ))}
  </div>
</div>
```

**Alternative: Visual Flow Diagram**
```jsx
// Using a tree/flow diagram library like react-flow or vis.js
const nodes = [
  { id: 'REQ-013', label: 'REQ-013', type: 'requirement' },
  ...response.linked_test_cases.map(tc => ({
    id: tc.test_id,
    label: `${tc.test_id}: ${tc.title}`,
    type: 'test_case'
  })),
  ...response.compliance_standards.map(std => ({
    id: std.standard_id,
    label: std.standard_name,
    type: 'compliance'
  }))
];

const edges = response.traceability_chain.map((chain, idx) => ({
  id: `edge-${idx}`,
  source: chain.test_case_id || response.requirement.id,
  target: chain.compliance_standard_id,
  label: chain.direct_relationship ? 'Direct' : 'Via Test',
  style: { stroke: chain.direct_relationship ? '#ff6b6b' : '#4ecdc4' }
}));
```

---

### 3. Linked Test Cases Section

```
┌─────────────────────────────────────────────────────────────┐
│  Linked Test Cases (2)                                     │
│  ────────────────────                                      │
│                                                             │
│  • TC_005: GDPR Data Minimization Compliance               │
│    Category: Compliance Tests | Priority: High            │
│                                                             │
│  • TC_013: View Audit Logs                                  │
│    Category: Functional Tests | Priority: Medium          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```jsx
<div className="linked-test-cases">
  <h3>Linked Test Cases ({response.metadata.total_test_cases})</h3>
  <ul>
    {response.linked_test_cases.map(testCase => (
      <li key={testCase.test_id} className="test-case-item">
        <div className="test-case-header">
          <strong>{testCase.test_id}:</strong> {testCase.title}
        </div>
        <div className="test-case-meta">
          Category: <span className="badge">{testCase.category}</span> | 
          Priority: <span className={`priority priority-${testCase.priority.toLowerCase()}`}>
            {testCase.priority}
          </span>
        </div>
      </li>
    ))}
  </ul>
</div>
```

---

### 4. Compliance Standards Section

```
┌─────────────────────────────────────────────────────────────┐
│  Compliance Standards (2)                                  │
│  ────────────────────                                      │
│                                                             │
│  • GDPR:2016/679 (GDPR)                                    │
│  • HIPAA:45-CFR-164 (HIPAA)                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
```jsx
<div className="compliance-standards">
  <h3>Compliance Standards ({response.metadata.total_compliance_standards})</h3>
  <ul>
    {response.compliance_standards.map(standard => (
      <li key={standard.standard_id} className="compliance-item">
        <span className="standard-name">{standard.standard_name}</span>
        <span className={`standard-type type-${standard.standard_type.toLowerCase()}`}>
          {standard.standard_type}
        </span>
      </li>
    ))}
  </ul>
</div>
```

---

## Complete React Component Example

```jsx
import React from 'react';

const TraceabilityView = ({ traceabilityData }) => {
  const { requirement, linked_test_cases, compliance_standards, traceability_chain, metadata } = traceabilityData;

  return (
    <div className="traceability-modal">
      {/* Header */}
      <div className="modal-header">
        <h2>View Traceability: {requirement.id}</h2>
      </div>

      {/* Requirement Details */}
      <div className="requirement-section">
        <h3>Requirement Details</h3>
        <div className="requirement-info">
          <div><strong>ID:</strong> {requirement.id}</div>
          <div><strong>Text:</strong> {requirement.text}</div>
          <div>
            <strong>Page:</strong> {requirement.page} | 
            <strong> Confidence:</strong> {(requirement.confidence * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Traceability Chain */}
      <div className="chain-section">
        <h3>Traceability Chain</h3>
        <div className="chain-diagram">
          {/* Root: Requirement */}
          <div className="node requirement-node">
            {requirement.id}
          </div>

          {/* Group by test case */}
          {linked_test_cases.map(testCase => {
            const testChains = traceability_chain.filter(
              c => c.test_case_id === testCase.test_id
            );
            
            return (
              <div key={testCase.test_id} className="chain-group">
                <div className="arrow-down">↓</div>
                <div className="node test-node">
                  <div className="node-header">
                    {testCase.test_id}: {testCase.title}
                  </div>
                </div>
                
                {/* Compliance standards for this test */}
                {testChains.map((chain, idx) => (
                  <div key={idx} className="chain-branch">
                    <div className="arrow-right">→</div>
                    <div className="node compliance-node">
                      {chain.compliance_standard_name}
                      {chain.inferred_from_data && (
                        <span className="badge inferred">Inferred</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}

          {/* Direct relationships */}
          {traceability_chain
            .filter(c => c.direct_relationship)
            .map((chain, idx) => (
              <div key={`direct-${idx}`} className="chain-group direct-relation">
                <div className="arrow-right">→</div>
                <div className="node compliance-node">
                  {chain.compliance_standard_name}
                  <span className="badge direct">Direct</span>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Linked Test Cases */}
      <div className="test-cases-section">
        <h3>Linked Test Cases ({metadata.total_test_cases})</h3>
        <div className="test-cases-list">
          {linked_test_cases.map(testCase => (
            <div key={testCase.test_id} className="test-case-card">
              <div className="test-case-id">{testCase.test_id}</div>
              <div className="test-case-title">{testCase.title}</div>
              <div className="test-case-meta">
                <span className="badge category">{testCase.category}</span>
                <span className={`badge priority priority-${testCase.priority.toLowerCase()}`}>
                  {testCase.priority}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Compliance Standards */}
      <div className="compliance-section">
        <h3>Compliance Standards ({metadata.total_compliance_standards})</h3>
        <div className="compliance-list">
          {compliance_standards.map(standard => (
            <div key={standard.standard_id} className="compliance-card">
              <div className="standard-name">{standard.standard_name}</div>
              <div className={`standard-type type-${standard.standard_type.toLowerCase()}`}>
                {standard.standard_type}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Metadata Summary */}
      <div className="metadata-footer">
        <small>
          {metadata.chain_paths} chain paths | 
          {metadata.total_test_cases} test cases | 
          {metadata.total_compliance_standards} standards
        </small>
      </div>
    </div>
  );
};

export default TraceabilityView;
```

---

## CSS Styling Example

```css
.traceability-modal {
  padding: 20px;
  max-width: 900px;
}

.requirement-section {
  margin-bottom: 30px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.chain-section {
  margin-bottom: 30px;
}

.chain-diagram {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.node {
  padding: 10px 15px;
  border-radius: 6px;
  font-weight: 500;
}

.requirement-node {
  background: #4a90e2;
  color: white;
  font-size: 18px;
  text-align: center;
}

.test-node {
  background: #50c878;
  color: white;
  margin-left: 30px;
}

.compliance-node {
  background: #ffa500;
  color: white;
  margin-left: 30px;
}

.chain-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chain-branch {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 60px;
}

.arrow-down, .arrow-right {
  color: #666;
  font-weight: bold;
}

.badge {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.badge.inferred {
  background: #fff3cd;
  color: #856404;
}

.badge.direct {
  background: #d1ecf1;
  color: #0c5460;
}

.test-cases-list, .compliance-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.test-case-card, .compliance-card {
  padding: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fff;
}

.test-case-card:hover, .compliance-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transform: translateY(-2px);
  transition: all 0.2s;
}

.priority-high { color: #dc3545; }
.priority-medium { color: #ffc107; }
.priority-low { color: #28a745; }

.type-gdpr { background: #4a90e2; color: white; }
.type-hipaa { background: #50c878; color: white; }
.type-fda { background: #ff6b6b; color: white; }
```

---

## Alternative: Tree View Component

For a more interactive visualization, use a tree view:

```jsx
import { Tree } from 'react-d3-tree';

const TraceabilityTree = ({ traceabilityData }) => {
  const { requirement, traceability_chain } = traceabilityData;

  // Build tree structure
  const treeData = {
    name: requirement.id,
    children: traceability_chain
      .filter(c => c.test_case_id)
      .reduce((acc, chain) => {
        const existing = acc.find(a => a.name === chain.test_case_id);
        if (existing) {
          existing.children.push({
            name: chain.compliance_standard_name,
            attributes: { type: chain.compliance_standard_type }
          });
        } else {
          acc.push({
            name: chain.test_case_id,
            attributes: { title: chain.test_case_title },
            children: [{
              name: chain.compliance_standard_name,
              attributes: { type: chain.compliance_standard_type }
            }]
          });
        }
        return acc;
      }, [])
      .concat(
        traceability_chain
          .filter(c => c.direct_relationship)
          .map(c => ({
            name: c.compliance_standard_name,
            attributes: { type: 'direct', standardType: c.compliance_standard_type }
          }))
      )
  };

  return (
    <div style={{ width: '100%', height: '600px' }}>
      <Tree
        data={treeData}
        orientation="vertical"
        pathFunc="step"
        translate={{ x: 400, y: 50 }}
      />
    </div>
  );
};
```

---

## Summary

**Display Format:**
1. **Header**: Requirement ID and basic info
2. **Requirement Details**: ID, text, page, confidence
3. **Traceability Chain**: Visual diagram showing REQ → TC → Compliance relationships
4. **Linked Test Cases**: List of test cases with metadata
5. **Compliance Standards**: List of standards with types
6. **Metadata Footer**: Summary counts

**Key Visual Elements:**
- Use color coding: Requirements (blue), Test Cases (green), Compliance (orange)
- Show badges for inferred vs direct relationships
- Use arrows/connectors to show flow
- Make it responsive and interactive
- Highlight direct relationships differently from inferred ones

