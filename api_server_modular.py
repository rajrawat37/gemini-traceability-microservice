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
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import modular components
from modules.document_ai import extract_traceable_docai
from modules.dlp_masking import mask_chunks_with_dlp
from modules.rag_enhancement import query_rag_from_chunks
from modules.knowledge_graph import build_knowledge_graph_from_rag, analyze_test_coverage, create_flow_visualization
from modules.test_generation import generate_test_cases_with_rag_context, enrich_test_cases_for_ui

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
            "/generate-ui-tests": "POST - COMPLETE UI PIPELINE: DocAI→DLP→RAG→KG→Gemini with enhanced traceability"
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
    file: UploadFile = File(...),
    use_mock: bool = False,
    gdpr_mode: bool = True
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
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
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
    gdpr_mode: bool = True
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
    
    Args:
        file: PDF file to process
        gdpr_mode: If True (default), performs PII masking
    
    Returns:
        Complete pipeline output with enhanced traceability and KG integration
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
