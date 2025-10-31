# Traceability API Endpoint

## Endpoint: `/get-traceability`

**Method**: `POST`

**Description**: Returns structured traceability data for a test case or requirement, extracted from the `/generate-ui-tests` response.

## Request Parameters

### Query Parameters
- `test_case_id` (optional): Test case ID (e.g., `TC_005`)
- `requirement_id` (optional): Requirement ID (e.g., `REQ-005`)
- **Note**: At least one of `test_case_id` or `requirement_id` must be provided

### Request Body
The full JSON response from `/generate-ui-tests` endpoint. Must include:
- `knowledge_graph`
- `test_suite`
- `compliance_dashboard`
- `flow_visualization`

## Response Structure

```json
{
  "status": "success",
  "requirement": {
    "id": "REQ-005",
    "text": "Full requirement text here...",
    "page": 1,
    "confidence": 0.9
  },
  "linked_test_cases": [
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
  ],
  "compliance_standards": [
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
  ],
  "traceability_chain": [
    {
      "requirement_id": "REQ-005",
      "test_case_id": "TC_005",
      "test_case_title": "Test Case Title",
      "compliance_standard_id": "GDPR:2016/679",
      "compliance_standard_name": "GDPR:2016/679",
      "compliance_standard_type": "GDPR"
    },
    {
      "requirement_id": "REQ-005",
      "test_case_id": "TC_006",
      "test_case_title": "Another Test Case",
      "compliance_standard_id": "HIPAA:45-CFR-164",
      "compliance_standard_name": "HIPAA:45-CFR-164",
      "compliance_standard_type": "HIPAA"
    },
    {
      "requirement_id": "REQ-005",
      "test_case_id": null,
      "test_case_title": null,
      "compliance_standard_id": "FDA:21-CFR-11",
      "compliance_standard_name": "FDA:21-CFR-11",
      "compliance_standard_type": "FDA",
      "direct_relationship": true
    }
  ],
  "metadata": {
    "requirement_id": "REQ-005",
    "test_case_id": "TC_005",
    "total_test_cases": 2,
    "total_compliance_standards": 3,
    "chain_paths": 3
  }
}
```

## Usage Examples

### Example 1: Get Traceability by Test Case ID

```bash
curl -X POST "http://localhost:8080/get-traceability?test_case_id=TC_005" \
  -H "Content-Type: application/json" \
  -d @response.json
```

Where `response.json` contains the full response from `/generate-ui-tests`.

### Example 2: Get Traceability by Requirement ID

```bash
curl -X POST "http://localhost:8080/get-traceability?requirement_id=REQ-005" \
  -H "Content-Type: application/json" \
  -d @response.json
```

### Example 3: Using JavaScript/TypeScript

```javascript
// First, get the full response from generate-ui-tests
const fullResponse = await fetch('http://localhost:8080/generate-ui-tests', {
  method: 'POST',
  body: formData  // FormData with PDF file
});

const pipelineData = await fullResponse.json();

// Then, get traceability for a specific test case
const traceabilityResponse = await fetch(
  'http://localhost:8080/get-traceability?test_case_id=TC_005',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(pipelineData)
  }
);

const traceabilityData = await traceabilityResponse.json();

// Use the data to display traceability view
console.log(traceabilityData.requirement);          // Requirement details
console.log(traceabilityData.linked_test_cases);    // All linked test cases
console.log(traceabilityData.compliance_standards); // All compliance standards
console.log(traceabilityData.traceability_chain);   // Chain visualization data
```

### Example 4: Python Client

```python
import requests

# Step 1: Generate UI tests
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8080/generate-ui-tests',
        files=files,
        params={'gdpr_mode': True}
    )
    pipeline_data = response.json()

# Step 2: Get traceability for a test case
traceability_response = requests.post(
    'http://localhost:8080/get-traceability',
    params={'test_case_id': 'TC_005'},
    json=pipeline_data
)

traceability_data = traceability_response.json()

print(f"Requirement: {traceability_data['requirement']['id']}")
print(f"Linked Test Cases: {len(traceability_data['linked_test_cases'])}")
print(f"Compliance Standards: {len(traceability_data['compliance_standards'])}")
```

## Response Fields Explained

### `requirement`
- `id`: Requirement identifier (e.g., "REQ-005")
- `text`: Full requirement text
- `page`: PDF page number where requirement was found
- `confidence`: Confidence score (0.0 to 1.0)

### `linked_test_cases`
Array of all test cases that verify this requirement:
- `test_id`: Test case identifier
- `title`: Test case title
- `category`: Test category (Security, Compliance, Functional, etc.)
- `priority`: Priority level (Critical, High, Medium, Low)

### `compliance_standards`
Array of all compliance standards governing this requirement:
- `standard_id`: Standard identifier
- `standard_name`: Standard name/title
- `standard_type`: Type (GDPR, HIPAA, FDA, etc.)

### `traceability_chain`
Array of chain paths showing relationships:
- `requirement_id`: Source requirement
- `test_case_id`: Linked test case (null for direct relationships)
- `test_case_title`: Test case title
- `compliance_standard_id`: Linked compliance standard
- `compliance_standard_name`: Compliance standard name
- `compliance_standard_type`: Standard type
- `direct_relationship`: true if REQ → Compliance (no test case in between)

### `metadata`
Summary statistics:
- `requirement_id`: The requirement ID queried
- `test_case_id`: The test case ID queried (if any)
- `total_test_cases`: Number of linked test cases
- `total_compliance_standards`: Number of compliance standards
- `chain_paths`: Number of traceability chain paths

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Either test_case_id or requirement_id must be provided"
}
```

### 404 Not Found
```json
{
  "detail": "Test case 'TC_999' not found in response data"
}
```

or

```json
{
  "detail": "Requirement 'REQ-999' not found in response data"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Traceability extraction error: [error message]"
}
```

## Integration with Frontend

This endpoint is designed to be called after the user clicks "View Traceability" on a test case card:

```javascript
async function viewTraceability(testCaseId, pipelineResponse) {
  try {
    const response = await fetch(
      `/get-traceability?test_case_id=${testCaseId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pipelineResponse)
      }
    );
    
    const data = await response.json();
    
    // Display traceability view
    showTraceabilityModal({
      requirement: data.requirement,
      testCases: data.linked_test_cases,
      complianceStandards: data.compliance_standards,
      chain: data.traceability_chain
    });
  } catch (error) {
    console.error('Failed to load traceability:', error);
  }
}
```

## Performance Notes

- This endpoint processes data in-memory and is fast (~10-50ms)
- No external API calls are made
- Response size is typically < 50KB
- Suitable for real-time UI updates

