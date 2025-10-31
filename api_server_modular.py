"""
Modular FastAPI Server for PDF Processing
Complete pipeline: Document AI + DLP + RAG + Knowledge Graph + Test Case Generation
For Cloud Run deployment
"""

import os

# Configure gRPC settings before any imports to suppress fork warnings
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '1'
os.environ['GRPC_POLL_STRATEGY'] = 'poll'

from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Body, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import modular components
from modules.document_ai import extract_traceable_docai
from modules.dlp_masking import mask_chunks_with_dlp
from modules.rag_enhancement import query_rag_from_chunks
from modules.knowledge_graph import build_knowledge_graph_from_rag, analyze_test_coverage, create_flow_visualization, generate_audit_report
from modules.test_generation import generate_test_cases_with_rag_context, generate_test_cases_batch, enrich_test_cases_for_ui

# Import GDPR compliance modules
from modules.gdpr_compliance import (
    get_user_data,
    update_user_data,
    delete_user_data,
    restrict_user_processing,
    export_user_data,
    grant_consent,
    withdraw_consent,
    get_consent_status
)
from modules.audit_logger import log_audit, get_audit_logs, get_processing_statistics, generate_ropa_report, get_client_ip, get_user_agent
from modules.breach_detection import check_rate_limit, track_auth_failure, detect_unusual_access, get_active_alerts, get_breach_statistics

app = FastAPI(
    title="Secure PDF Processor API with Knowledge Graph & Test Generation",
    description="Complete compliance pipeline: Extract text, mask PII, enhance with RAG, build knowledge graph, generate test cases",
    version="3.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API information endpoint"""
    return {
        "name": "Secure PDF Processor with Knowledge Graph & Test Generation",
        "version": "3.0.0",
        "description": "Complete compliance pipeline: Extract, mask PII, enhance with RAG, build knowledge graph, generate test cases",
        "pipeline": "Document AI → DLP → RAG → Knowledge Graph → Test Generation",
        "features": {
            "document_ai": "Extract text from PDFs",
            "dlp_masking": "Mask 9 types of PII",
            "rag_enhancement": "Query RAG corpus for insights",
            "knowledge_graph": "Build compliance graph (Requirements, Regulations, Articles, TestCases)",
            "test_generation": "Generate security/traceability/compliance/functional tests"
        },
        "relationships": [
            "VERIFIED_BY (Requirement → TestCase)",
            "GOVERNED_BY (Requirement → Regulation)",
            "ENSURES_COMPLIANCE_WITH (TestCase → ComplianceArticle)"
        ],
        "endpoints": {
            "/": "GET - API information",
            "/health": "GET - Health check",
            "/extract-document": "POST - Document AI extraction (PDF → structured text + entities)",
            "/extract-mask": "POST - Document AI + DLP masking (PDF → extraction + PII masking)",
            "/rag-enhance": "POST - Document AI + DLP + RAG enhancement (PDF → extraction + PII masking + RAG corpus)",
            "/build-knowledge-graph": "POST - Document AI + DLP + RAG + KG construction (PDF → knowledge graph with nodes & edges)",
            "/generate-ui-tests": "POST - COMPLETE UI PIPELINE: DocAI→DLP→RAG→KG→Gemini with enhanced traceability (supports batch_mode for 250+ tests)",
            "/get-traceability": "POST - Get structured traceability data for a test case or requirement (requires response from /generate-ui-tests)"
        },
        "rag_integration": "✅ Now uses YOUR Google Cloud RAG corpus (not hardcoded policies)",
        "rag_corpus_env": "Set RAG_CORPUS_NAME and RAG_LOCATION in environment variables"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pdf-processor-with-kg-and-test-gen",
        "pipeline": "Document AI → DLP → RAG → Knowledge Graph → Test Generation",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# GDPR COMPLIANCE ENDPOINTS
# ============================================================

@app.get("/user/{user_id}/data")
async def get_user_data_endpoint(user_id: str):
    """
    Art. 15 - Right to Access

    Retrieve all data stored for a specific user.

    Returns:
        - User profile
        - Processed documents
        - Consent history
        - Processing activities
    """
    result = await get_user_data(user_id)
    return result


@app.patch("/user/{user_id}/data")
async def update_user_data_endpoint(
    user_id: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None
):
    """
    Art. 16 - Right to Rectification

    Allow users to correct inaccurate personal data.
    """
    result = await update_user_data(user_id, email, full_name)
    return result


@app.delete("/user/{user_id}")
async def delete_user_data_endpoint(
    user_id: str,
    reason: Optional[str] = Query(None)
):
    """
    Art. 17 - Right to Erasure ("Right to be Forgotten")

    Delete all user data and related records.
    """
    result = await delete_user_data(user_id, reason)
    return result


@app.post("/user/{user_id}/restrict")
async def restrict_user_processing_endpoint(
    user_id: str,
    restrict: bool = Query(..., description="True to restrict, False to unrestrict")
):
    """
    Art. 18 - Right to Restriction of Processing

    Allow users to restrict processing of their data.
    """
    result = await restrict_user_processing(user_id, restrict)
    return result


@app.get("/user/{user_id}/export")
async def export_user_data_endpoint(
    user_id: str,
    format: str = Query("json", description="Export format: json or csv")
):
    """
    Art. 20 - Right to Data Portability

    Export all user data in machine-readable format.
    """
    result = await export_user_data(user_id, format)
    return result


@app.post("/consent")
async def grant_consent_endpoint(
    user_id: str = Query(...),
    consent_type: str = Query(..., description="Type: data_processing, marketing, analytics"),
    request: Optional[dict] = None
):
    """
    Art. 7 - Consent Requirements

    Record user consent for specific processing activities.
    """
    # Extract IP and user agent from request if available
    ip_address = None
    user_agent = None

    result = await grant_consent(
        user_id=user_id,
        consent_type=consent_type,
        ip_address=ip_address,
        user_agent=user_agent
    )
    return result


@app.delete("/consent")
async def withdraw_consent_endpoint(
    user_id: str = Query(...),
    consent_type: str = Query(...)
):
    """
    Art. 7(3) - Withdrawal of Consent

    Allow users to withdraw consent.
    """
    result = await withdraw_consent(user_id, consent_type)
    return result


@app.get("/consent/{user_id}")
async def get_consent_status_endpoint(user_id: str):
    """
    Get current consent status for a user.
    """
    result = await get_consent_status(user_id)
    return result


# ============================================================
# GDPR ADMIN/MONITORING ENDPOINTS
# ============================================================

@app.get("/admin/audit-logs")
async def get_audit_logs_endpoint(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100)
):
    """
    Art. 30 - Records of Processing Activities

    Query audit logs with filters.
    """
    result = await get_audit_logs(user_id, action, None, None, limit)
    return {"status": "success", "logs": result}


@app.get("/admin/processing-statistics")
async def get_processing_statistics_endpoint(
    user_id: Optional[str] = Query(None)
):
    """
    Art. 30 - Processing Activity Statistics

    Get processing activity statistics for ROPA reports.
    """
    result = await get_processing_statistics(user_id)
    return result


@app.get("/admin/ropa-report")
async def get_ropa_report_endpoint():
    """
    Art. 30 - Records of Processing Activities Report

    Generate ROPA-compliant report.
    """
    result = await generate_ropa_report()
    return result


@app.get("/admin/breach-alerts")
async def get_breach_alerts_endpoint(
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical")
):
    """
    Art. 33 - Breach Notification

    Get all active breach alerts.
    """
    result = await get_active_alerts(severity)
    return {"status": "success", "alerts": result}


@app.get("/admin/breach-statistics")
async def get_breach_statistics_endpoint(
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Art. 33 - Breach Statistics

    Get breach detection statistics.
    """
    result = await get_breach_statistics(days)
    return result


# ============================================================
# DOCUMENT PROCESSING ENDPOINTS
# ============================================================

@app.post("/extract-document")
async def extract_document_endpoint(
    file: UploadFile = File(...),
    use_mock: bool = False
):
    """
    📄 Document AI Extraction: Extract text and entities from PDF
    
    Upload PDF and get structured text extraction with entities using Google Cloud Document AI.
    
    Args:
        file: PDF file to process
        use_mock: If True, use mock data instead of actual Document AI API (default: False)
    
    Returns:
        Document AI extraction results with:
        - Extracted text chunks by page
        - Detected entities (requirements, compliance standards, etc.)
        - Metadata (page count, entity statistics, etc.)
    
    Example:
        curl -X POST "http://localhost:8080/extract-document?use_mock=false" \\
             -F "file=@document.pdf" \\
             -H "Content-Type: multipart/form-data"
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        project_id = os.getenv("PROJECT_ID", "401328495550")
        location = os.getenv("LOCATION", "us")
        processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")
        
        print(f"\n{'='*80}")
        print(f"📄 DOCUMENT AI EXTRACTION")
        print(f"{'='*80}")
        print(f"📁 File: {file.filename}")
        print(f"🔧 Mock Mode: {use_mock}")
        print(f"🏗️  Project: {project_id}")
        print(f"📍 Processor: projects/{project_id}/locations/{location}/processors/{processor_id}")
        
        # Read file content
        content = await file.read()
        
        # Extract with Document AI
        print(f"\n📄 Extracting document content...")
        docai_result = extract_traceable_docai(
            content=content,
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            document_name=file.filename,
            use_mock=use_mock
        )
        
        print(f"\n{'='*80}")
        print(f"✅ DOCUMENT AI EXTRACTION COMPLETE")
        print(f"{'='*80}\n")
        
        # 4️⃣ Normalize response envelope - move filename/mock_mode to source_document
        if "source_document" in docai_result:
            docai_result["source_document"]["filename"] = file.filename
            docai_result["source_document"]["mock_mode"] = use_mock
        
        # Return normalized response (no duplicate statistics block)
        return docai_result
    
    except Exception as e:
        print(f"\n❌ Document AI extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document AI extraction error: {str(e)}")


@app.post("/extract-mask")
async def extract_mask_endpoint(
    file: UploadFile = File(..., description="PDF file to process (required)"),
    use_mock: bool = Query(False, description="Use mock data instead of actual APIs"),
    gdpr_mode: bool = Query(True, description="Enable PII masking with DLP")
):
    """
    🔒 Document AI + DLP Masking: Extract text and mask PII in one step
    
    Upload PDF and get structured text extraction with automatic PII masking using 
    Google Cloud Document AI and DLP API.
    
    This endpoint combines:
    1. Document AI extraction (text, entities, compliance, requirements)
    2. DLP PII masking (GDPR-compliant data protection)
    
    Optimizations:
    - Returns unified chunks with both original_text and masked_text
    - Uses asyncio.to_thread() to prevent DLP API blocking
    - Includes per-chunk trace_links for traceability
    - Simplified response structure (no redundant fields)
    
    Args:
        file: PDF file to process
        use_mock: If True, use mock data instead of actual Document AI API (default: False)
        gdpr_mode: If True, performs PII masking (default: True)
    
    Returns:
        Simplified response schema:
        {
          "status": "success",
          "agent": "Document AI + DLP",
          "document": {...document metadata...},
          "chunks": [...unified chunks with original_text, masked_text, trace_links...],
          "summary": {...combined statistics...},
          "processor": {...processor info...}
        }
    
    Example:
        curl -X POST "http://localhost:8080/extract-mask?gdpr_mode=true" \\
             -F "file=@document.pdf" \\
             -H "Content-Type: multipart/form-data"
    """
    # FastAPI automatically validates file is present (422 error if missing)
    # Check file extension
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported. Please upload a PDF file.")
    
    try:
        project_id = os.getenv("PROJECT_ID", "401328495550")
        location = os.getenv("LOCATION", "us")
        processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")
        
        print(f"\n{'='*80}")
        print(f"📄🔒 DOCUMENT AI + DLP MASKING PIPELINE")
        print(f"{'='*80}")
        print(f"📁 File: {file.filename}")
        print(f"🔧 Mock Mode: {use_mock}")
        print(f"🔒 GDPR Mode: {gdpr_mode}")
        print(f"🏗️  Project: {project_id}")
        
        # Read file content
        content = await file.read()
        
        # Step 1: Document AI extraction
        print(f"\n📄 Step 1: Document AI extraction...")
        docai_result = extract_traceable_docai(
            content=content,
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            document_name=file.filename,
            use_mock=use_mock
        )
        
        # Step 2: DLP masking (returns unified chunks with trace_links)
        print(f"🔒 Step 2: DLP masking (GDPR mode: {gdpr_mode})...")
        # Pick DLP location: prefer same region as Document AI if set; fallback to env DLP_LOCATION or 'us'
        dlp_location = os.getenv("DLP_LOCATION", os.getenv("LOCATION", "us"))
        dlp_result = await mask_chunks_with_dlp(
            docai_result,
            project_id,
            gdpr_mode=gdpr_mode,
            location=dlp_location
        )
        
        print(f"\n{'='*80}")
        print(f"✅ DOCUMENT AI + DLP MASKING COMPLETE")
        print(f"{'='*80}\n")
        
        # Build clean, flattened response schema (no duplicate fields)
        response = {
            "status": "success",
            "agent": "Document AI + DLP",
            
            # Document metadata - single source of truth (no duplication)
            "document": {
                **docai_result.get("source_document", {}),
                "filename": file.filename,
                "mock_mode": use_mock,
                "gdpr_mode": gdpr_mode
            },
            
            # Unified chunks with per-chunk PII stats (no global duplication)
            "chunks": dlp_result.get("chunks", []),
            
            # Combined summary (Document AI + aggregated DLP statistics)
            "summary": {
                # Document AI stats
                "total_pages": dlp_result.get("summary", {}).get("total_pages", 0),
                "total_chunks": dlp_result.get("summary", {}).get("total_chunks", 0),
                "requirements_found": dlp_result.get("summary", {}).get("requirements_found", 0),
                "compliance_standards_found": dlp_result.get("summary", {}).get("compliance_standards_found", 0),
                "total_edges": dlp_result.get("summary", {}).get("total_edges", 0),
                "kg_ready": dlp_result.get("summary", {}).get("kg_ready", True),
                
                # Aggregated DLP stats (per-chunk details available in chunks[].pii_*)
                "pii_masking_performed": dlp_result.get("summary", {}).get("pii_masking_performed", False),
                "chunks_with_pii": dlp_result.get("summary", {}).get("chunks_with_pii", 0)
            },
            
            # Processor info
            "processor": docai_result.get("processor", {})
        }
        
        return response
    
    except Exception as e:
        print(f"\n❌ Extract-mask error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Extract-mask error: {str(e)}")


@app.post("/rag-enhance")
async def rag_enhance_endpoint(
    file: UploadFile = File(...),
    use_mock: bool = Query(False),
    gdpr_mode: bool = Query(True),
    rag_corpus_name: Optional[str] = Query(None),
    rag_location: str = Query("europe-west3")
):
    """
    🔍 RAG Enhancement: Extract text, mask PII, and enhance with RAG corpus
    
    Upload PDF and get:
    1. Document AI text extraction with entities
    2. DLP PII masking (GDPR-compliant)
    3. RAG corpus enhancement for compliance insights
    
    Args:
        file: PDF file to process
        use_mock: Use mock data instead of real APIs (for testing)
        gdpr_mode: Enable PII masking with DLP (default: True)
        rag_corpus_name: Custom RAG corpus name (optional)
        rag_location: RAG corpus location (default: "europe-west3")
    
    Returns:
        JSON with extracted text, masked chunks, and RAG-enhanced compliance insights
    """
    try:
        print(f"\n🔍 RAG Enhancement Pipeline Starting...")
        print(f"   File: {file.filename}")
        print(f"   GDPR Mode: {gdpr_mode}")
        print(f"   RAG Location: {rag_location}")

        # Get environment variables
        project_id = os.getenv("PROJECT_ID", "poc-genai-hacks")
        location = os.getenv("LOCATION", "us")
        processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")

        # Read file content
        content = await file.read()

        # Step 1: Document AI extraction
        print(f"\n📄 Step 1: Document AI Extraction...")
        docai_result = extract_traceable_docai(
            content=content,
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            document_name=file.filename,
            use_mock=use_mock
        )

        if docai_result.get("status") != "success":
            raise HTTPException(status_code=500, detail=f"Document AI failed: {docai_result.get('error', 'Unknown error')}")
        
        # Step 2: DLP masking
        print(f"\n🔒 Step 2: DLP PII Masking...")
        dlp_location = os.getenv("DLP_LOCATION", location)
        
        dlp_result = await mask_chunks_with_dlp(
            docai_result,
            project_id,
            gdpr_mode=gdpr_mode,
            location=dlp_location
        )
        
        # Step 3: RAG enhancement
        print(f"\n🔍 Step 3: RAG Corpus Enhancement...")
        rag_result = await query_rag_from_chunks(
            dlp_result,
            project_id,
            rag_corpus_name=rag_corpus_name,
            rag_location=rag_location
        )
        
        if rag_result.get("status") != "success":
            print(f"⚠️  RAG enhancement failed: {rag_result.get('error', 'Unknown error')}")
            # Continue with DLP result even if RAG fails
            rag_result = {
                "status": "partial_success",
                "agent": "RAG-Enhanced",
                "context_docs": [],
                "metadata": {
                    "total_chunks_processed": 0,
                    "total_policies_matched": 0,
                    "chunks_with_policies": 0,
                    "rag_corpus_used": "none",
                    "rag_location": rag_location,
                    "error": rag_result.get("error", "RAG processing failed")
                }
            }
        
        # Combine results
        response = {
            "status": "success",
            "agent": "Document AI + DLP + RAG",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4()),
            
            # Document metadata
            "document": {
                "filename": file.filename,
                "mock_mode": use_mock,
                "gdpr_mode": gdpr_mode,
                "rag_location": rag_location,
                "rag_corpus": rag_corpus_name or "default"
            },
            
            # Processed chunks with RAG enhancement
            "chunks": dlp_result.get("chunks", []),
            
            # RAG-enhanced context documents
            "context_docs": rag_result.get("context_docs", []),
            
            # Summary statistics
            "summary": {
                **dlp_result.get("summary", {}),
                "rag_enhancement": rag_result.get("metadata", {}),
                "total_context_docs": len(rag_result.get("context_docs", [])),
                "policies_matched": rag_result.get("metadata", {}).get("total_policies_matched", 0)
            },
            
            # Processor info
            "processor": docai_result.get("processor", {})
        }
        
        print(f"\n✅ RAG Enhancement Complete!")
        print(f"   Chunks processed: {len(dlp_result.get('chunks', []))}")
        print(f"   Context docs: {len(rag_result.get('context_docs', []))}")
        print(f"   Policies matched: {rag_result.get('metadata', {}).get('total_policies_matched', 0)}")
        
        return response
    
    except Exception as e:
        print(f"\n❌ RAG enhancement error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG enhancement error: {str(e)}")


@app.post("/build-knowledge-graph")
async def build_knowledge_graph_endpoint(
    file: UploadFile = File(...),
    use_mock: bool = Query(False),
    gdpr_mode: bool = Query(True),
    rag_corpus_name: Optional[str] = Query(None),
    rag_location: str = Query("europe-west3")
):
    """
    🕸️ Build Knowledge Graph: Extract text, mask PII, enhance with RAG, and build KG

    Upload PDF and get:
    1. Document AI text extraction with entities
    2. DLP PII masking (GDPR-compliant)
    3. RAG corpus enhancement for compliance insights
    4. Knowledge Graph construction (nodes, edges, relationships)

    Args:
        file: PDF file to process
        use_mock: Use mock data instead of real APIs (for testing)
        gdpr_mode: Enable PII masking with DLP (default: True)
        rag_corpus_name: Custom RAG corpus name (optional)
        rag_location: RAG corpus location (default: "europe-west3")

    Returns:
        JSON with knowledge graph nodes, edges, and comprehensive metadata
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        print(f"\n{'='*80}")
        print(f"🕸️ KNOWLEDGE GRAPH CONSTRUCTION PIPELINE")
        print(f"{'='*80}")
        print(f"📄 File: {file.filename}")
        print(f"🔧 Mock Mode: {use_mock}")
        print(f"🔒 GDPR Mode: {gdpr_mode}")
        print(f"🔍 RAG Location: {rag_location}")

        # Get environment variables
        project_id = os.getenv("PROJECT_ID", "poc-genai-hacks")
        location = os.getenv("LOCATION", "us")
        processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")

        # Read file content
        content = await file.read()

        # Step 1: Document AI extraction
        print(f"\n📄 Step 1: Document AI Extraction...")
        docai_result = extract_traceable_docai(
            content=content,
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            document_name=file.filename,
            use_mock=use_mock
        )

        if docai_result.get("status") != "success":
            raise HTTPException(status_code=500, detail=f"Document AI failed: {docai_result.get('error', 'Unknown error')}")

        # Step 2: DLP masking
        print(f"\n🔒 Step 2: DLP PII Masking...")
        dlp_location = os.getenv("DLP_LOCATION", location)

        dlp_result = await mask_chunks_with_dlp(
            docai_result,
            project_id,
            gdpr_mode=gdpr_mode,
            location=dlp_location
        )

        # Step 3: RAG enhancement
        print(f"\n🔍 Step 3: RAG Corpus Enhancement...")
        rag_result = await query_rag_from_chunks(
            dlp_result,
            project_id,
            rag_corpus_name=rag_corpus_name,
            rag_location=rag_location
        )

        if rag_result.get("status") != "success":
            print(f"⚠️  RAG enhancement failed: {rag_result.get('error', 'Unknown error')}")
            # Continue with DLP result even if RAG fails
            rag_result = {
                "status": "partial_success",
                "agent": "RAG-Enhanced",
                "chunks": dlp_result.get("chunks", []),
                "context_docs": [],
                "metadata": {
                    "total_chunks_processed": 0,
                    "total_policies_matched": 0,
                    "chunks_with_policies": 0,
                    "rag_corpus_used": "none",
                    "rag_location": rag_location,
                    "error": rag_result.get("error", "RAG processing failed")
                }
            }

        # Step 4: Knowledge Graph construction
        print(f"\n🕸️  Step 4: Knowledge Graph Construction...")
        kg_result = build_knowledge_graph_from_rag(rag_result)

        if kg_result.get("status") != "success":
            raise HTTPException(status_code=500, detail=f"Knowledge Graph construction failed: {kg_result.get('error', 'Unknown error')}")

        print(f"\n{'='*80}")
        print(f"✅ KNOWLEDGE GRAPH CONSTRUCTION COMPLETE")
        print(f"{'='*80}")
        print(f"   Nodes: {len(kg_result.get('nodes', []))}")
        print(f"   Edges: {len(kg_result.get('edges', []))}")
        print(f"   Requirements: {kg_result.get('metadata', {}).get('requirement_nodes', 0)}")
        print(f"   Compliance Standards: {kg_result.get('metadata', {}).get('compliance_nodes', 0)}")

        # Build response
        response = {
            "status": "success",
            "agent": "Knowledge Graph Builder",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4()),

            # Document metadata
            "document": {
                "filename": file.filename,
                "mock_mode": use_mock,
                "gdpr_mode": gdpr_mode,
                "rag_location": rag_location,
                "rag_corpus": rag_corpus_name or "default"
            },

            # Knowledge Graph
            "knowledge_graph": {
                "nodes": kg_result.get("nodes", []),
                "edges": kg_result.get("edges", []),
                "metadata": kg_result.get("metadata", {})
            },

            # Pipeline summary
            "pipeline_summary": {
                "docai": {
                    "status": "success",
                    "chunks_extracted": len(docai_result.get("chunks", [])),
                    "pages_processed": docai_result.get("summary", {}).get("total_pages", 0)
                },
                "dlp": {
                    "status": "success",
                    "pii_masking_performed": dlp_result.get("summary", {}).get("pii_masking_performed", False),
                    "chunks_with_pii": dlp_result.get("summary", {}).get("chunks_with_pii", 0)
                },
                "rag": {
                    "status": rag_result.get("status", "unknown"),
                    "policies_matched": rag_result.get("metadata", {}).get("total_policies_matched", 0),
                    "chunks_with_policies": rag_result.get("metadata", {}).get("chunks_with_policies", 0)
                },
                "kg": {
                    "status": kg_result.get("status", "unknown"),
                    "total_nodes": len(kg_result.get("nodes", [])),
                    "total_edges": len(kg_result.get("edges", [])),
                    "graph_density": kg_result.get("metadata", {}).get("graph_density", 0)
                }
            }
        }

        return response

    except Exception as e:
        print(f"\n❌ Knowledge Graph construction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Knowledge Graph construction error: {str(e)}")


@app.post("/generate-ui-tests")
async def generate_ui_tests_endpoint(
    file: UploadFile = File(...),
    gdpr_mode: bool = True,
    batch_mode: bool = Query(False, description="Enable batch generation for large test counts"),
    test_count: int = Query(50, description="Target number of test cases (only used in batch mode, default: 50)")
):
    """
    🚀 COMPLETE UI PIPELINE: DocAI → DLP → RAG → KG → Gemini with enhanced traceability

    Upload PDF and get the complete compliance traceability pipeline with:
    1. Extract text and entities with Document AI (traceable chunks)
    2. Mask PII with DLP (GDPR-compliant)
    3. Enrich with RAG (policy matching using YOUR corpus)
    4. Build Knowledge Graph (nodes, edges, relationships)
    5. Generate test cases with Gemini (using RAG context + KG relationships)
    6. Enhanced traceability with KG mapping
    7. Test coverage analysis
    8. Flow visualization (requirement → test → compliance)
    9. Compliance dashboard data (audit readiness, gaps, standards coverage)

    Args:
        file: PDF file to process
        gdpr_mode: If True (default), performs PII masking
        batch_mode: If True, use parallel batch generation for large test counts (default: False)
        test_count: Target number of test cases to generate in batch mode (default: 50, max recommended: 250)

    Performance:
        - Normal mode: ~15 tests in 35 seconds
        - Batch mode (250 tests): ~250 tests in 45 seconds (6x faster per test)

    Returns:
        Complete pipeline output with:
        - test_suite: Test categories, statistics, PDF outline
        - knowledge_graph: Nodes, edges, metadata
        - flow_visualization: Requirement → test → compliance mapping
        - compliance_summary: Quick stats for home screen card (coverage, status, top 3 standards)
        - compliance_dashboard: Full dashboard data (overview, gaps, standards coverage, audit report)
        - pipeline_metadata: Step-by-step execution status
        - enhanced_traceability: KG utilization, coverage score, flow metrics
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        project_id = os.getenv("PROJECT_ID", "poc-genai-hacks")
        location = os.getenv("LOCATION", "us")
        processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")
        rag_corpus_name = os.getenv("RAG_CORPUS_NAME", "projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856")
        rag_location = os.getenv("RAG_LOCATION", "europe-west3")
        gemini_location = os.getenv("GEMINI_LOCATION", "us-central1")
        
        print(f"\n{'='*80}")
        print(f"🚀 STARTING COMPLETE UI PIPELINE")
        print(f"{'='*80}")
        print(f"📄 File: {file.filename}")
        print(f"🔒 GDPR Mode: {gdpr_mode}")
        print(f"🏗️  Project: {project_id}")
        print(f"🔍 RAG Corpus: {rag_corpus_name}")
        print(f"🤖 Gemini Location: {gemini_location}")
        if batch_mode:
            print(f"🚀 Batch Mode: ENABLED (target: {test_count} tests)")
            print(f"⏱️  Expected time: ~45-60 seconds for {test_count} test cases")
        else:
            print(f"📝 Batch Mode: DISABLED (standard ~15 tests)")
            print(f"⏱️  Expected time: 25-40 seconds for complete pipeline")
        
        # Read file content
        content = await file.read()
        
        # Step 1: Document AI extraction
        print(f"\n📄 Step 1: Document AI extraction...")
        docai_result = extract_traceable_docai(content, project_id, location, processor_id, file.filename)
        
        # Step 2: DLP masking
        print(f"🔒 Step 2: DLP masking (GDPR mode: {gdpr_mode})...")
        dlp_result = await mask_chunks_with_dlp(docai_result, project_id, gdpr_mode=gdpr_mode)
        
        # Step 3: RAG enhancement
        print(f"🔍 Step 3: RAG enhancement...")
        rag_result = await query_rag_from_chunks(dlp_result, project_id, rag_corpus_name, rag_location)
        
        # Step 4: Knowledge Graph construction
        print(f"🕸️  Step 4: Knowledge Graph construction...")
        kg_result = build_knowledge_graph_from_rag(rag_result)
        
        # Step 5: Test case generation with KG context
        print(f"🧪 Step 5: Test case generation with KG context...")
        if batch_mode:
            print(f"   🚀 BATCH MODE ENABLED: Generating {test_count} test cases in parallel...")
            test_result = await generate_test_cases_batch(rag_result, project_id, gemini_location, kg_result, test_count)
        else:
            print(f"   📝 Normal mode: Generating ~15 test cases...")
            test_result = generate_test_cases_with_rag_context(rag_result, project_id, gemini_location, kg_result)
        
        # Step 6: UI enrichment with enhanced traceability
        print(f"🎨 Step 6: UI enrichment with enhanced traceability...")
        ui_result = enrich_test_cases_for_ui(
            test_result.get("test_cases", []),
            kg_result,
            rag_result,
            dlp_result
        )
        
        # Step 7: Flow visualization
        print(f"📊 Step 7: Flow visualization...")
        flow_visualization = create_flow_visualization(ui_result, kg_result)

        # Step 8: Generate audit report and compliance dashboard data
        print(f"📋 Step 8: Generating compliance dashboard data...")
        audit_report = generate_audit_report(kg_result, ui_result.get("test_categories", []), rag_result)

        # Extract compliance metrics for dashboard
        coverage_analysis = ui_result.get("coverage_analysis", {})
        coverage_score = coverage_analysis.get("coverage_score", 0)

        # Calculate status indicators based on coverage score
        if coverage_score >= 90:
            status = "COMPLIANT"
            status_icon = "🟢"
            status_color = "#4CAF50"  # Green
        elif coverage_score >= 70:
            status = "READY_WITH_GAPS"
            status_icon = "🟡"
            status_color = "#FFA500"  # Orange
        else:
            status = "AT_RISK"
            status_icon = "🔴"
            status_color = "#F44336"  # Red

        # Get all compliance standards from KG
        kg_nodes = kg_result.get("nodes", [])
        kg_edges = kg_result.get("edges", [])
        compliance_standards = [n for n in kg_nodes if n.get("type") == "COMPLIANCE_STANDARD"]
        requirements = [n for n in kg_nodes if n.get("type") == "REQUIREMENT"]

        # Calculate coverage for each standard
        standards_coverage_list = []
        for comp in compliance_standards:
            comp_id = comp.get("id")
            comp_name = comp.get("title", "Unknown")
            comp_type = comp.get("standard_type", "UNKNOWN")

            # Find requirements linked to this standard
            reqs_for_standard = [edge.get("from") for edge in kg_edges if edge.get("to") == comp_id]
            total_reqs = len(reqs_for_standard)

            # Count verified requirements (those with test cases)
            verified_reqs = 0
            all_test_cases = []
            for category in ui_result.get("test_categories", []):
                all_test_cases.extend(category.get("test_cases", []))

            for req_id in reqs_for_standard:
                has_tests = any(test.get("derived_from") == req_id for test in all_test_cases)
                if has_tests:
                    verified_reqs += 1

            coverage_pct = (verified_reqs / total_reqs * 100) if total_reqs > 0 else 0

            # Assign status and color
            if coverage_pct == 100:
                std_status = "✅"
                std_color = "#4CAF50"
                std_text_status = "COMPLIANT"
            elif coverage_pct >= 70:
                std_status = "🟡"
                std_color = "#FFA500"
                std_text_status = "PARTIAL"
            else:
                std_status = "🔴"
                std_color = "#F44336"
                std_text_status = "AT_RISK"

            standards_coverage_list.append({
                "standard_id": comp_id,
                "standard_name": comp_name,
                "standard_type": comp_type,
                "coverage": round(coverage_pct, 1),
                "status": std_status,
                "status_text": std_text_status,
                "color": std_color,
                "requirements_total": total_reqs,
                "requirements_verified": verified_reqs,
                "requirements_unverified": total_reqs - verified_reqs
            })

        # Sort by coverage percentage (descending)
        standards_coverage_list.sort(key=lambda x: x["coverage"], reverse=True)

        # Get top 3 standards for summary card
        top_3_standards = standards_coverage_list[:3]

        # Extract gaps from coverage analysis
        coverage_gaps = coverage_analysis.get("coverage_gaps", [])
        critical_gaps_count = len([g for g in coverage_gaps if g.get("severity") == "high"])

        # Build gap objects with PDF locations
        gaps_with_locations = []
        for gap in coverage_gaps:
            gap_type = gap.get("type", "unknown")

            # Try to extract requirement ID from gap message
            gap_message = gap.get("message", "")

            gaps_with_locations.append({
                "gap_id": f"GAP-{len(gaps_with_locations) + 1:03d}",
                "severity": gap.get("severity", "medium").upper(),
                "type": gap_type,
                "message": gap_message,
                "issue": gap_message,
                "recommendation": "Review and add test cases for missing coverage"
            })

        # Build compliance_summary for home screen card
        compliance_summary = {
            "coverage_score": round(coverage_score, 1),
            "status": status,
            "status_icon": status_icon,
            "status_color": status_color,
            "quick_stats": {
                "total_requirements": len(requirements),
                "requirements_tested": coverage_analysis.get("total_requirements", 0),
                "requirements_untested": len(requirements) - coverage_analysis.get("total_requirements", 0),
                "total_tests": ui_result.get("statistics", {}).get("total_tests", 0),
                "critical_gaps": critical_gaps_count
            },
            "top_standards": [
                {
                    "name": std["standard_name"],
                    "coverage": std["coverage"],
                    "status": std["status"],
                    "color": std["color"]
                }
                for std in top_3_standards
            ]
        }

        # Build compliance_dashboard for full dashboard tab
        compliance_dashboard = {
            "overview": {
                "audit_readiness": status,
                "coverage_score": round(coverage_score, 1),
                "total_requirements": len(requirements),
                "requirements_tested": coverage_analysis.get("total_requirements", 0),
                "requirements_untested": len(requirements) - coverage_analysis.get("total_requirements", 0),
                "total_tests": ui_result.get("statistics", {}).get("total_tests", 0),
                "total_compliance_standards": len(compliance_standards)
            },
            "gaps": gaps_with_locations,
            "standards_coverage": standards_coverage_list,
            "audit_report": audit_report
        }

        print(f"✅ Compliance dashboard data generated")
        print(f"   Coverage Score: {coverage_score}%")
        print(f"   Status: {status} {status_icon}")
        print(f"   Standards Tracked: {len(standards_coverage_list)}")
        print(f"   Critical Gaps: {critical_gaps_count}")

        print(f"\n{'='*80}")
        print(f"✅ UI-READY TEST GENERATION COMPLETE")
        print(f"{'='*80}\n")

        response_data = {
            "status": "success",
            "agent": "Complete Test Generation Pipeline with UI Integration",
            "filename": file.filename,
            "gdpr_mode": gdpr_mode,
            
            # Main output for UI
            "test_suite": {
                "test_categories": ui_result.get("test_categories", []),
                "statistics": ui_result.get("statistics", {}),
                "pdf_outline": ui_result.get("pdf_outline", {})
            },
            
            # Knowledge Graph for visualization
            "knowledge_graph": {
                "nodes": kg_result.get("nodes", []),
                "edges": kg_result.get("edges", []),
                "metadata": kg_result.get("metadata", {})
            },
            
            # 🚀 NEW: Flow visualization (requirement → test → compliance)
            "flow_visualization": flow_visualization,

            # 🎯 NEW: Compliance Summary (for home screen card)
            "compliance_summary": compliance_summary,

            # 📊 NEW: Compliance Dashboard (for dashboard tab)
            "compliance_dashboard": compliance_dashboard,

            # Pipeline metadata
            "pipeline_metadata": {
                "step_1_docai": {
                    "status": "success",
                    "chunks_extracted": len(docai_result.get("chunks", [])),
                    "entities_found": docai_result.get("metadata", {}).get("total_detected_entities", 0)
                },
                "step_2_dlp": {
                    "status": "success",
                    "chunks_masked": len(dlp_result.get("masked_chunks", [])),
                    "pii_found": dlp_result.get("metadata", {}).get("total_pii_found", 0)
                },
                "step_3_rag": {
                    "status": "success",
                    "context_docs": len(rag_result.get("context_docs", [])),
                    "policies_matched": rag_result.get("metadata", {}).get("total_policies_matched", 0)
                },
                "step_4_kg": {
                    "status": kg_result.get("status", "unknown"),
                    "nodes_created": len(kg_result.get("nodes", [])),
                    "edges_created": len(kg_result.get("edges", []))
                },
                "step_5_tests": {
                    "status": test_result.get("status", "unknown"),
                    "tests_generated": len(test_result.get("test_cases", [])),
                    "model_used": test_result.get("metadata", {}).get("model_used", "unknown")
                },
                "step_6_ui": {
                    "status": ui_result.get("status", "unknown"),
                    "categories_created": len(ui_result.get("test_categories", [])),
                    "total_tests": ui_result.get("statistics", {}).get("total_tests", 0)
                },
                "step_7_flow": {
                    "status": flow_visualization.get("status", "unknown"),
                    "requirements_mapped": flow_visualization.get("total_requirements", 0),
                    "compliance_standards_mapped": flow_visualization.get("total_compliance_standards", 0)
                },
                "step_8_compliance": {
                    "status": "success",
                    "audit_report_generated": audit_report.get("status", "unknown") == "success",
                    "compliance_standards_tracked": len(standards_coverage_list),
                    "coverage_score": coverage_score,
                    "audit_readiness": status
                }
            },
            
            # Enhanced traceability
            "enhanced_traceability": {
                "kg_utilization": ui_result.get("coverage_analysis", {}).get("kg_utilization", {}),
                "coverage_score": ui_result.get("coverage_analysis", {}).get("coverage_score", 0),
                "flow_metrics": flow_visualization.get("flow_metrics", {})
            }
        }
        
        # Add coverage analysis to response
        if ui_result.get("coverage_analysis"):
            response_data["coverage_analysis"] = ui_result["coverage_analysis"]
        
        return response_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UI test generation error: {str(e)}")


def sanitize_for_json(obj):
    """
    Recursively sanitize data to ensure it's JSON-serializable.
    Converts bytes to strings and handles other non-serializable types.
    """
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Convert other types to string
        try:
            return str(obj)
        except Exception:
            return None


def build_traceability_chain(requirement_id: str, knowledge_graph: dict) -> list:
    """
    Build traceability chain visualization: REQ → TC → Compliance
    
    Returns list of chain paths showing the relationships
    """
    chain_paths = []
    kg_nodes = knowledge_graph.get("nodes", [])
    kg_edges = knowledge_graph.get("edges", [])
    
    if not kg_nodes or not kg_edges:
        return chain_paths
    
    # Get all test cases for this requirement
    # Check both VERIFIED_BY relation and direct connections
    test_edges = [
        e for e in kg_edges 
        if e.get("from") == requirement_id and 
        (e.get("relation") == "VERIFIED_BY" or 
         e.get("relation") == "verified_by" or
         e.get("type") == "VERIFIED_BY")
    ]
    
    for test_edge in test_edges:
        test_id = test_edge.get("to")
        
        # Find test case node for additional info
        test_node = next((n for n in kg_nodes if n.get("id") == test_id and n.get("type") == "TEST_CASE"), None)
        
        # Get compliance standards for this test case
        # Check multiple possible relation names
        compliance_edges = [
            e for e in kg_edges 
            if e.get("from") == test_id and 
            (e.get("relation") == "ENSURES_COMPLIANCE_WITH" or
             e.get("relation") == "ensures_compliance_with" or
             e.get("type") == "ENSURES_COMPLIANCE_WITH")
        ]
        
        for comp_edge in compliance_edges:
            comp_node = next((n for n in kg_nodes if n.get("id") == comp_edge.get("to") and n.get("type") == "COMPLIANCE_STANDARD"), None)
            
            if comp_node:
                chain_paths.append({
                    "requirement_id": str(requirement_id),
                    "test_case_id": str(test_id) if test_id else None,
                    "test_case_title": str(test_node.get("title", test_id) if test_node else test_id),
                    "compliance_standard_id": str(comp_node.get("id", "")),
                    "compliance_standard_name": str(comp_node.get("title", "")),
                    "compliance_standard_type": str(comp_node.get("standard_type", "UNKNOWN"))
                })
    
    # Also get direct REQ → Compliance relationships
    req_to_comp_edges = [
        e for e in kg_edges 
        if e.get("from") == requirement_id and 
        (e.get("relation") == "GOVERNED_BY" or
         e.get("relation") == "governed_by" or
         e.get("type") == "GOVERNED_BY")
    ]
    
    for comp_edge in req_to_comp_edges:
        comp_node = next((n for n in kg_nodes if n.get("id") == comp_edge.get("to") and n.get("type") == "COMPLIANCE_STANDARD"), None)
        
        if comp_node:
            chain_paths.append({
                "requirement_id": str(requirement_id),
                "test_case_id": None,  # Direct relationship
                "test_case_title": None,
                "compliance_standard_id": str(comp_node.get("id", "")),
                "compliance_standard_name": str(comp_node.get("title", "")),
                "compliance_standard_type": str(comp_node.get("standard_type", "UNKNOWN")),
                "direct_relationship": True
            })
    
    return chain_paths


@app.post("/get-traceability", response_class=JSONResponse)
async def get_traceability_endpoint(
    request: Request,
    test_case_id: Optional[str] = Query(None, description="Test case ID (e.g., TC_005). Either test_case_id or requirement_id is required."),
    requirement_id: Optional[str] = Query(None, description="Requirement ID (e.g., REQ-005). Either test_case_id or requirement_id is required."),
    response_data: Optional[Dict[str, Any]] = Body(None, description="Full response from /generate-ui-tests endpoint (must be JSON, not file upload)")
):
    """
    🔗 Get Structured Traceability Data
    
    Returns structured traceability information for a test case or requirement.
    This endpoint extracts and formats traceability data from the /generate-ui-tests response.
    
    **Usage:**
    - Pass `test_case_id` to view traceability from a test case perspective
    - Pass `requirement_id` to view traceability from a requirement perspective
    - Pass the full JSON response from `/generate-ui-tests` as the request body
    
    **Returns:**
    - Requirement details (ID, text, page, confidence)
    - Linked test cases (all tests for the requirement)
    - Compliance standards (all standards governing the requirement)
    - Traceability chain (visual representation of relationships)
    
    **Example Request:**
    ```json
    POST /get-traceability?test_case_id=TC_005
    {
      "knowledge_graph": {...},
      "test_suite": {...},
      "compliance_dashboard": {...},
      "flow_visualization": {...}
    }
    ```
    
    **Example Response:**
    ```json
    {
      "requirement": {
        "id": "REQ-005",
        "text": "Full requirement text",
        "page": 1,
        "confidence": 0.9
      },
      "linked_test_cases": [
        {
          "test_id": "TC_005",
          "title": "Test Title",
          "category": "Security Tests",
          "priority": "High"
        }
      ],
      "compliance_standards": [
        {
          "standard_id": "GDPR:2016/679",
          "standard_name": "GDPR:2016/679",
          "standard_type": "GDPR"
        }
      ],
      "traceability_chain": [...]
    }
    ```
    """
    try:
        # Check content type to prevent file uploads
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            raise HTTPException(
                status_code=400,
                detail="This endpoint does NOT accept file uploads. It expects JSON data. Usage: 1) First call POST /generate-ui-tests with your PDF file, 2) Then call POST /get-traceability with the JSON response from step 1 as the request body (with Content-Type: application/json)."
            )
        
        if not test_case_id and not requirement_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Missing required parameter",
                    "message": "Either 'test_case_id' or 'requirement_id' must be provided as a query parameter",
                    "example_usage": [
                        "POST /get-traceability?test_case_id=TC_005",
                        "POST /get-traceability?requirement_id=REQ-005"
                    ],
                    "hint": "If you know the test case ID, use test_case_id. If you know the requirement ID, use requirement_id."
                }
            )
        
        if not response_data:
            raise HTTPException(
                status_code=400,
                detail="Request body must contain JSON data from /generate-ui-tests endpoint. This endpoint does NOT accept file uploads. First call /generate-ui-tests to get the response, then pass that JSON response to this endpoint."
            )
        
        # Check if response_data looks like it might be from the wrong endpoint
        if isinstance(response_data, bytes):
            raise HTTPException(
                status_code=400,
                detail="This endpoint expects JSON data, not a file upload. Please call /generate-ui-tests first to get the response data, then pass that JSON response to this endpoint."
            )
        
        # Sanitize input data first to handle any bytes objects
        response_data = sanitize_for_json(response_data)
        
        # Extract data from response
        knowledge_graph = response_data.get("knowledge_graph", {})
        test_suite = response_data.get("test_suite", {})
        compliance_dashboard = response_data.get("compliance_dashboard", {})
        flow_visualization = response_data.get("flow_visualization", {})
        
        kg_nodes = knowledge_graph.get("nodes", [])
        kg_edges = knowledge_graph.get("edges", [])
        test_categories = test_suite.get("test_categories", [])
        audit_report = compliance_dashboard.get("audit_report", {})
        traceability_matrix = audit_report.get("traceability_matrix", [])
        requirement_coverage = flow_visualization.get("requirement_coverage", [])
        
        # Determine requirement_id
        if test_case_id and not requirement_id:
            # Find test case and get its derived_from
            test_case = None
            for category in test_categories:
                test_case = next((tc for tc in category.get("test_cases", []) if tc.get("test_id") == test_case_id), None)
                if test_case:
                    break
            
            if not test_case:
                raise HTTPException(
                    status_code=404,
                    detail=f"Test case '{test_case_id}' not found in response data"
                )
            
            requirement_id = test_case.get("derived_from")
            if not requirement_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Test case '{test_case_id}' does not have a linked requirement (derived_from field missing)"
                )
        
        # Get requirement details
        # First try traceability_matrix (most complete)
        req_entry = next((t for t in traceability_matrix if t.get("requirement_id") == requirement_id), None)
        
        if req_entry:
            # Use traceability_matrix data (most complete)
            requirement_details = {
                "id": str(req_entry.get("requirement_id", "")),
                "text": str(req_entry.get("requirement_full_text") or req_entry.get("requirement_text", "")),
                "page": req_entry.get("page_number") if isinstance(req_entry.get("page_number"), (int, float)) else None,
                "confidence": float(req_entry.get("confidence", 0.0)) if isinstance(req_entry.get("confidence"), (int, float)) else 0.0
            }
            
            # Sanitize test cases and compliance standards from traceability matrix
            linked_test_cases_raw = req_entry.get("test_cases", [])
            linked_test_cases = [
                {
                    "test_id": str(tc.get("test_id", "")),
                    "title": str(tc.get("title", "")),
                    "category": str(tc.get("category", "")),
                    "priority": str(tc.get("priority", ""))
                }
                for tc in linked_test_cases_raw
            ]
            
            compliance_standards_raw = req_entry.get("compliance_standards", [])
            # Deduplicate compliance standards by standard_id
            seen_std_ids = set()
            compliance_standards = []
            for std in compliance_standards_raw:
                std_id = str(std.get("standard_id", ""))
                if std_id and std_id not in seen_std_ids:
                    seen_std_ids.add(std_id)
                    compliance_standards.append({
                        "standard_id": std_id,
                        "standard_name": str(std.get("standard_name", "")),
                        "standard_type": str(std.get("standard_type", "UNKNOWN"))
                    })
            
        else:
            # Fallback: get from knowledge_graph nodes
            req_node = next((n for n in kg_nodes if n.get("id") == requirement_id and n.get("type") == "REQUIREMENT"), None)
            
            if not req_node:
                raise HTTPException(
                    status_code=404,
                    detail=f"Requirement '{requirement_id}' not found in response data"
                )
            
            requirement_details = {
                "id": str(req_node.get("id", "")),
                "text": str(req_node.get("text", "")),
                "page": req_node.get("page_number") if isinstance(req_node.get("page_number"), (int, float)) else None,
                "confidence": float(req_node.get("confidence", 0.0)) if isinstance(req_node.get("confidence"), (int, float)) else 0.0
            }
            
            # Get linked test cases from flow_visualization or test_suite
            req_coverage = next((r for r in requirement_coverage if r.get("requirement_id") == requirement_id), None)
            
            if req_coverage:
                linked_test_cases_raw = req_coverage.get("test_cases", [])
                linked_test_cases = [
                    {
                        "test_id": str(tc.get("test_id", "")),
                        "title": str(tc.get("title", "")),
                        "category": str(tc.get("category", "")),
                        "priority": str(tc.get("priority", ""))
                    }
                    for tc in linked_test_cases_raw
                ]
                # Get compliance standard details
                compliance_names = req_coverage.get("compliance_standards", [])
                compliance_standards = []
                
                # Deduplicate compliance standards
                seen_std_ids = set()
                for std_name in compliance_names:
                    std_node = next((n for n in kg_nodes if n.get("type") == "COMPLIANCE_STANDARD" and (n.get("title") == std_name or n.get("id") == std_name)), None)
                    if std_node:
                        std_id = str(std_node.get("id", ""))
                        if std_id and std_id not in seen_std_ids:
                            seen_std_ids.add(std_id)
                            compliance_standards.append({
                                "standard_id": std_id,
                                "standard_name": str(std_node.get("title", "")),
                                "standard_type": str(std_node.get("standard_type", "UNKNOWN"))
                            })
            else:
                # Fallback: search all test cases
                all_test_cases = []
                for category in test_categories:
                    all_test_cases.extend(category.get("test_cases", []))
                
                linked_test_cases = [
                    {
                        "test_id": str(tc.get("test_id", "")),
                        "title": str(tc.get("title", "")),
                        "category": str(tc.get("category", "")),
                        "priority": str(tc.get("priority", ""))
                    }
                    for tc in all_test_cases if tc.get("derived_from") == requirement_id
                ]
                
                # Get compliance standards from edges
                compliance_edges = [e for e in kg_edges if e.get("from") == requirement_id and e.get("relation") == "GOVERNED_BY"]
                compliance_standards = []
                
                # Deduplicate compliance standards
                seen_std_ids = set()
                for edge in compliance_edges:
                    comp_node = next((n for n in kg_nodes if n.get("id") == edge.get("to") and n.get("type") == "COMPLIANCE_STANDARD"), None)
                    if comp_node:
                        std_id = str(comp_node.get("id", ""))
                        if std_id and std_id not in seen_std_ids:
                            seen_std_ids.add(std_id)
                            compliance_standards.append({
                                "standard_id": std_id,
                                "standard_name": str(comp_node.get("title", "")),
                                "standard_type": str(comp_node.get("standard_type", "UNKNOWN"))
                            })
        
        # Build traceability chain
        traceability_chain = build_traceability_chain(requirement_id, knowledge_graph)
        
        # If no chain found from KG edges, try to build from linked test cases and compliance standards
        if not traceability_chain and linked_test_cases and compliance_standards:
            # Build chain from available data - create one entry per test case linking to all compliance standards
            # Group by test case to avoid creating too many entries
            seen_chains = set()  # Track (test_id, std_id) pairs to avoid duplicates
            
            for test_case in linked_test_cases:
                test_id = test_case.get("test_id")
                # For each test case, create a chain entry showing it connects to requirement and compliance standards
                # We'll create one entry per test case that lists all compliance standards
                for std in compliance_standards:
                    std_id = str(std.get("standard_id", ""))
                    chain_key = (test_id, std_id)
                    if chain_key not in seen_chains:
                        seen_chains.add(chain_key)
                        traceability_chain.append({
                            "requirement_id": str(requirement_id),
                            "test_case_id": str(test_id) if test_id else None,
                            "test_case_title": str(test_case.get("title", "")),
                            "compliance_standard_id": std_id,
                            "compliance_standard_name": str(std.get("standard_name", "")),
                            "compliance_standard_type": str(std.get("standard_type", "UNKNOWN")),
                            "inferred_from_data": True  # Indicates this was inferred, not from KG edges
                        })
            
            # Also add direct REQ → Compliance relationships (deduplicated)
            seen_direct = set()
            for std in compliance_standards:
                std_id = str(std.get("standard_id", ""))
                if std_id not in seen_direct:
                    seen_direct.add(std_id)
                    traceability_chain.append({
                        "requirement_id": str(requirement_id),
                        "test_case_id": None,
                        "test_case_title": None,
                        "compliance_standard_id": std_id,
                        "compliance_standard_name": str(std.get("standard_name", "")),
                        "compliance_standard_type": str(std.get("standard_type", "UNKNOWN")),
                        "direct_relationship": True,
                        "inferred_from_data": True
                    })
        
        # Format response
        result = {
            "status": "success",
            "requirement": requirement_details,
            "linked_test_cases": linked_test_cases,
            "compliance_standards": compliance_standards,
            "traceability_chain": traceability_chain,
            "metadata": {
                "requirement_id": str(requirement_id) if requirement_id else None,
                "test_case_id": str(test_case_id) if test_case_id else None,
                "total_test_cases": len(linked_test_cases),
                "total_compliance_standards": len(compliance_standards),
                "chain_paths": len(traceability_chain)
            }
        }
        
        # Sanitize response to ensure all data is JSON-serializable
        sanitized_result = sanitize_for_json(result)
        
        return sanitized_result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Traceability endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Traceability extraction error: {str(e)}")


# ============================================================
# SERVER STARTUP
# ============================================================

if __name__ == "__main__":
    print("🚀 Starting Modular Secure PDF Processor API...")
    print("📁 Modules loaded:")
    print("   - Document AI: PDF text extraction")
    print("   - DLP Masking: PII detection and masking")
    print("   - RAG Enhancement: Policy matching")
    print("   - Knowledge Graph: Compliance relationships")
    print("   - Test Generation: AI-powered test cases")
    print("🔗 Main endpoint: /generate-ui-tests")
    print("📚 API docs: http://localhost:8080/docs")
    
    uvicorn.run(
        "api_server_modular:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
