# Postman Testing Guide

## Testing `/extract-mask` Endpoint

### Step-by-Step Instructions

#### 1. Open Postman and Create New Request

1. Click **"New"** button (top left)
2. Select **"HTTP Request"**
3. Name it: `Extract and Mask PDF`

#### 2. Configure Request Method and URL

1. **Method**: Select **POST** from dropdown
2. **URL**: Enter `http://localhost:8080/extract-mask`

#### 3. Add Query Parameters (Optional)

Click on **"Params"** tab below the URL:

| Key | Value | Description |
|-----|-------|-------------|
| `gdpr_mode` | `true` | Enable PII masking (default: true) |
| `use_mock` | `false` | Use real APIs (default: false) |

**Example URL with params:**
```
http://localhost:8080/extract-mask?gdpr_mode=true&use_mock=false
```

#### 4. Configure Request Body (IMPORTANT)

1. Click on **"Body"** tab
2. Select **"form-data"** (NOT raw or JSON!)
3. In the Key column:
   - Change the first dropdown from "Text" to **"File"** (important!)
   - Enter key name: `file` (exactly this name, case-sensitive)
   - Click **"Select Files"** or **"Choose Files"** button
   - Browse and select your PDF file

**Visual Guide:**
```
┌─────────────────────────────────────────┐
│ Body Tab                                │
├─────────────────────────────────────────┤
│ ○ form-data  ← SELECT THIS              │
│ ○ x-www-form-urlencoded                 │
│ ○ raw                                    │
│ ○ binary                                 │
│ ○ GraphQL                                │
├─────────────────────────────────────────┤
│ Key           │ Value        │ Options  │
├─────────────────────────────────────────┤
│ [File▼] file  │ [Select...]  │ [✓]     │
│   ↑           │              │         │
│   Must be     │ Click to     │ Keep    │
│   "File" type │ select PDF   │ checked │
└─────────────────────────────────────────┘
```

#### 5. Important Settings

- **Key name**: Must be exactly `file` (lowercase)
- **Type**: Must be set to **"File"** (use dropdown to change from "Text" to "File")
- **Value**: Click "Select Files" to choose your PDF

**❌ Common Mistakes:**
- Using key name `document`, `pdf`, `fileupload` (must be `file`)
- Selecting "Text" instead of "File" type
- Sending as JSON or raw data

#### 6. Headers (Auto-Generated)

Postman will automatically set:
- `Content-Type: multipart/form-data; boundary=...`

**DO NOT manually set Content-Type header** - Postman handles this automatically!

#### 7. Send Request

Click the blue **"Send"** button.

---

## Example Requests

### Request 1: Basic Extract and Mask (GDPR Enabled)

**Method**: `POST`  
**URL**: `http://localhost:8080/extract-mask?gdpr_mode=true`

**Body** (form-data):
- Key: `file` (type: File)
- Value: Select your PDF file

**Expected Response:**
```json
{
  "status": "success",
  "agent": "Document AI + DLP",
  "document": {
    "filename": "document.pdf",
    "gdpr_mode": true,
    ...
  },
  "chunks": [...],
  "summary": {
    "total_pages": 10,
    "pii_masking_performed": true,
    ...
  }
}
```

---

### Request 2: Extract Without Masking (GDPR Disabled)

**Method**: `POST`  
**URL**: `http://localhost:8080/extract-mask?gdpr_mode=false`

**Body** (form-data):
- Key: `file` (type: File)
- Value: Select your PDF file

---

### Request 3: Using Mock Data (For Testing)

**Method**: `POST`  
**URL**: `http://localhost:8080/extract-mask?use_mock=true&gdpr_mode=true`

**Body** (form-data):
- Key: `file` (type: File)
- Value: Select any PDF (won't be processed, uses mock data)

---

## Troubleshooting

### Error: "Field required" for "file"

**Problem**: File field is missing or incorrectly configured.

**Solution**:
1. Make sure you're in **"Body"** tab → **"form-data"**
2. Key name must be exactly `file`
3. Type must be **"File"** (not "Text")
4. You must actually select a file (don't leave it empty)

### Error: "Only PDF files are supported"

**Problem**: File is not a PDF.

**Solution**: Upload a `.pdf` file only.

### Error: Connection refused or timeout

**Problem**: Server is not running.

**Solution**: 
1. Start the server: `python api_server_modular.py` or `uvicorn api_server_modular:app --reload`
2. Check server is running on port 8080
3. Verify URL: `http://localhost:8080`

### Request hangs or takes too long

**Problem**: Processing large PDF or API calls are slow.

**Solution**: 
- For testing, use `use_mock=true` to get instant responses
- For real processing, be patient - Document AI and DLP can take 10-30 seconds

---

## Complete Postman Collection Setup

### Option 1: Manual Setup (Steps Above)

Follow the step-by-step instructions above.

### Option 2: Import Collection

1. In Postman, click **"Import"** button
2. Select **"File"** tab
3. Choose the Postman collection file (if available)
4. Or import from URL

### Option 3: Use Pre-configured Request

Create a new request with these exact settings:

**Request Configuration:**
```
Method: POST
URL: {{base_url}}/extract-mask?gdpr_mode=true

Headers: (Auto-generated, don't add manually)

Body: form-data
  Key: file (type: File)
  Value: [Select PDF file]
```

---

## Visual Postman Setup Checklist

```
☐ Method set to POST
☐ URL entered: http://localhost:8080/extract-mask
☐ Query params added (gdpr_mode, use_mock) - Optional
☐ Body tab selected
☐ form-data option selected (NOT raw/json)
☐ Key name is exactly "file"
☐ Key type is "File" (use dropdown)
☐ PDF file actually selected
☐ Send button clicked
```

---

## Testing Other Endpoints

### `/extract-document`

**Method**: `POST`  
**URL**: `http://localhost:8080/extract-document?use_mock=false`  
**Body**: form-data, Key: `file` (File type)

### `/generate-ui-tests`

**Method**: `POST`  
**URL**: `http://localhost:8080/generate-ui-tests?gdpr_mode=true`  
**Body**: form-data, Key: `file` (File type)

### `/get-traceability`

**Method**: `POST`  
**URL**: `http://localhost:8080/get-traceability?test_case_id=TC_005`  
**Body**: raw (JSON) - Paste the response from `/generate-ui-tests`

---

## Environment Variables (Optional)

For easier testing, create a Postman Environment:

1. Click **"Environments"** (left sidebar)
2. Click **"+"** to create new environment
3. Add variables:
   - `base_url`: `http://localhost:8080`
4. Use in requests: `{{base_url}}/extract-mask`

---

## Quick Test Script

In Postman, you can add a **"Tests"** script to validate the response:

```javascript
// Check response status
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Check response structure
pm.test("Response has status field", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('status');
    pm.expect(jsonData.status).to.eql('success');
});

// Check document metadata
pm.test("Response contains document info", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('document');
    pm.expect(jsonData.document).to.have.property('filename');
});
```

---

## Summary

**Key Points:**
1. ✅ Method: POST
2. ✅ Body: form-data (NOT JSON!)
3. ✅ Key name: `file` (exactly)
4. ✅ Type: File (use dropdown)
5. ✅ Actually select a PDF file
6. ✅ Query params are optional

**Common Mistakes:**
- ❌ Using JSON body
- ❌ Wrong key name
- ❌ Using "Text" type instead of "File"
- ❌ Not selecting a file

Follow these steps and your request should work!

