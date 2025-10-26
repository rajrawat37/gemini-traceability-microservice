"""
Document AI Module
Handles PDF text extraction, entity recognition, and intelligent requirement/compliance detection

Features:
- PDF text extraction with Document AI API integration
- Real bounding box extraction from layout.bounding_poly
- Regex-based compliance standard detection (GDPR, CCPA, HIPAA, SOC2, ISO27001, PCI-DSS, FDA)
- Rule-based requirement detection using modal verbs and bullet points
- Multiple label classification per chunk (security, compliance, technical, etc.)
- Canonical compliance IDs (GDPR:2016/679, CCPA:CA-CIV-1798.100, etc.)
- Automatic traceability edge generation (requirement → compliance)
- Page-level trace_links within chunks
- Knowledge graph ready output with normalized relationship types
- Text anchor tracking (start/end indices) for precise referencing
- Mock data support for testing and development

Response Structure:
- source_document: Document metadata with filename, mock_mode, timestamps
- chunks[]: Page-based text chunks with labels, detected requirements/compliance, trace_links
- edges[]: Traceability relationships with normalized types (entity_to_entity, rule_based)
- summary: Comprehensive statistics including kg_ready flag and total counts
- processor: Document AI processor metadata and endpoint information
"""

import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from google.cloud import documentai
from google.cloud.documentai_v1 import DocumentProcessorServiceClient
from .mock_data_loader import load_document_ai_mock


def load_mock_docai_response() -> dict:
    """
    🚀 Load mock Document AI response from external file
    
    This function loads a comprehensive mock Document AI response from the mockData
    directory, simulating a well-trained Document AI processor that accurately
    extracts requirements, compliance entities, and creates proper traceability links.
    """
    
    mock_data = load_document_ai_mock()
    
    # Update timestamp to current time if data was loaded successfully
    if mock_data and "source_document" in mock_data:
        mock_data["source_document"]["id"] = f"doc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        mock_data["source_document"]["processed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    return mock_data


def create_fallback_mock_response() -> dict:
    """
    Create a minimal fallback mock response if the external file is not available
    """
    return {
        "status": "success",
        "agent": "Document AI",
        "source_document": {
            "name": "PRD-3.pdf",
            "id": f"doc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")
        },
        "chunks": [],
        "metadata": {
            "total_pages": 1,
            "total_chunks": 0,
            "total_detected_entities": 0,
            "text_length": 0,
            "has_entities": False,
            "compliance_standards_found": 0,
            "requirements_found": 0,
            "total_compliance_links": 0
        }
    }


def extract_traceable_docai(content: bytes, project_id: str, location: str, processor_id: str, document_name: str = "document.pdf", use_mock: bool = False) -> dict:
    """
    🚀 PRODUCTION VERSION: Use actual Document AI API for text extraction and entity recognition
    Matches Node.js implementation structure with proper request format
    
    Args:
        content: PDF file content as bytes
        project_id: Google Cloud project ID
        location: Document AI processor location
        processor_id: Document AI processor ID
        document_name: Name of the document
        use_mock: If True, use mock data instead of actual API
        
    Returns:
        Structured Document AI response with extracted text and entities
    """
    
    # Check if mock mode is enabled
    if use_mock or os.getenv("USE_MOCK_DOCAI", "false").lower() == "true":
        print("🔧 MOCK MODE: Using mock Document AI response for testing")
        return load_mock_docai_response()
    
    try:
        print("🔧 PRODUCTION MODE: Using actual Document AI API")
        
        # Initialize the Document AI client
        client = DocumentProcessorServiceClient()
        
        # Construct the full resource name of the processor (matching Node.js)
        name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
        
        print(f"📄 Processing document with processor: {name}")
        print(f"📁 File info: {document_name}, size: {len(content)} bytes")
        
        # Determine MIME type
        mime_type = "application/pdf"
        if document_name.lower().endswith('.pdf'):
            mime_type = "application/pdf"
        elif document_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            mime_type = f"image/{document_name.split('.')[-1].lower()}"
        
        # Create the request payload - content field expects raw bytes, not base64
        request = documentai.ProcessRequest(
            name=name,
            skip_human_review=True,  # Matching Node.js skipHumanReview
            raw_document=documentai.RawDocument(
                content=content,  # Pass raw bytes directly
                mime_type=mime_type
            )
        )
        
        # Call the Document AI API to process the document
        print(f"🔄 Sending request to Document AI...")
        result = client.process_document(request=request)
        
        # Extract the document from the result
        document = result.document
        
        # DEBUG: Uncomment to see full API response
        # print("Full Document AI API Response:", document)
        
        # Prepare processor metadata
        processor_info = {
            "name": name,
            "project_id": project_id,
            "location": location,
            "processor_id": processor_id,
            "endpoint": f"https://{location}-documentai.googleapis.com/v1/{name}:process"
        }
        
        # Parse the document and extract structured data
        parsed_data = parse_document_ai_response(document, document_name, processor_info)
        
        print(f"✅ Document AI processing complete: {len(parsed_data.get('chunks', []))} chunks extracted")
        return parsed_data
        
    except Exception as e:
        print(f"⚠️  Document AI API error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Document AI processing failed: {str(e)}")


def get_bounding_poly(layout) -> dict:
    """
    Extract real bounding box coordinates from layout.bounding_poly
    
    Args:
        layout: Layout object with bounding_poly
        
    Returns:
        Dictionary with normalized coordinates or None
    """
    if not hasattr(layout, 'bounding_poly') or not layout.bounding_poly:
        return None
    
    bounding_poly = layout.bounding_poly
    if not hasattr(bounding_poly, 'normalized_vertices') or not bounding_poly.normalized_vertices:
        return None
    
    vertices = bounding_poly.normalized_vertices
    if len(vertices) < 2:
        return None
    
    # Get min/max from all vertices
    x_coords = [v.x for v in vertices if hasattr(v, 'x')]
    y_coords = [v.y for v in vertices if hasattr(v, 'y')]
    
    if not x_coords or not y_coords:
        return None
    
    return {
        "x_min": min(x_coords),
        "y_min": min(y_coords),
        "x_max": max(x_coords),
        "y_max": max(y_coords)
    }


def detect_compliance_standards(text: str) -> List[Dict[str, str]]:
    """
    2️⃣ Regex-based compliance detection in text with canonical IDs
    
    Args:
        text: Text to analyze
        
    Returns:
        List of detected compliance standards with canonical IDs
    """
    compliance_patterns = {
        'GDPR': {
            'patterns': [
                r'\bGDPR\b',
                r'General Data Protection Regulation',
                r'GDPR\s+Article\s+\d+',
                r'\bdata protection\b.*\bEU\b',
                r'\bright to be forgotten\b',
                r'\bdata subject rights\b'
            ],
            'canonical_id': 'GDPR:2016/679',
            'name': 'GDPR'
        },
        'CCPA': {
            'patterns': [
                r'\bCCPA\b',
                r'California Consumer Privacy Act',
                r'\bconsumer privacy rights\b.*\bCalifornia\b',
                r'\bdo not sell\b.*\bpersonal information\b'
            ],
            'canonical_id': 'CCPA:CA-CIV-1798.100',
            'name': 'CCPA'
        },
        'HIPAA': {
            'patterns': [
                r'\bHIPAA\b',
                r'Health Insurance Portability',
                r'\bPHI\b.*\bprotection\b',
                r'\bprotected health information\b',
                r'HIPAA\s+§\s*\d+'
            ],
            'canonical_id': 'HIPAA:45-CFR-164',
            'name': 'HIPAA'
        },
        'SOC2': {
            'patterns': [
                r'\bSOC\s*2\b',
                r'\bSOC2\b',
                r'SOC\s*2\s+Type\s+(I|II)',
                r'\bservice organization control\b'
            ],
            'canonical_id': 'SOC2:AICPA-TSC',
            'name': 'SOC2'
        },
        'ISO27001': {
            'patterns': [
                r'\bISO\s*27001\b',
                r'\bISO/IEC\s*27001\b',
                r'information security management'
            ],
            'canonical_id': 'ISO27001:2013',
            'name': 'ISO27001'
        },
        'PCI-DSS': {
            'patterns': [
                r'\bPCI\s*DSS\b',
                r'\bPCI-DSS\b',
                r'Payment Card Industry',
                r'\bcardholder data\b.*\bsecurity\b'
            ],
            'canonical_id': 'PCI-DSS:v4.0',
            'name': 'PCI-DSS'
        },
        'FDA_21CFR11': {
            'patterns': [
                r'\bFDA\s+21\s+CFR\s+Part\s+11\b',
                r'\b21\s+CFR\s+11\b',
                r'\belectronic signatures\b.*\bFDA\b'
            ],
            'canonical_id': 'FDA:21-CFR-11',
            'name': 'FDA 21 CFR Part 11'
        }
    }
    
    detected = []
    
    for standard_key, standard_info in compliance_patterns.items():
        for pattern in standard_info['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append({
                    'name': standard_info['name'],
                    'canonical_id': standard_info['canonical_id']
                })
                break  # Only add once per standard
    
    return detected


def detect_requirements(text: str) -> List[Dict[str, Any]]:
    """
    3️⃣ ENHANCED rule-based requirement detection with multiple strategies

    Detects requirements using:
    - Modal verbs (shall, must, should, will)
    - Key action verbs (provide, support, enable, allow, implement)
    - Bullet points and numbered lists
    - Section headers as high-level requirements
    - Feature/capability descriptions

    Args:
        text: Text to analyze

    Returns:
        List of detected requirements with metadata
    """
    requirements = []

    # 1️⃣ Modal verbs pattern (strict requirements)
    modal_verbs = [
        'shall', 'must', 'should', 'will', 'may',
        'needs to', 'required to', 'has to', 'ought to', 'supposed to'
    ]
    modal_pattern = r'\b(' + '|'.join(modal_verbs) + r')\b'

    # 2️⃣ Key action verbs (feature/capability requirements)
    action_verbs = [
        'provide', 'support', 'enable', 'allow', 'implement',
        'ensure', 'guarantee', 'deliver', 'offer', 'include',
        'facilitate', 'perform', 'execute', 'process', 'handle'
    ]
    action_pattern = r'\b(' + '|'.join(action_verbs) + r')(?:s|ing)?\b'

    # 3️⃣ Section header pattern (high-level requirements)
    section_pattern = r'^[A-Z][a-zA-Z\s&-]{3,40}:(?!\n)'  # "Feature Name:" or "Security:"

    # Split text into lines and sentences
    lines = text.split('\n')
    req_id_counter = 1
    seen_texts = set()  # Deduplication

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:  # Skip very short lines
            continue

        # Check for section headers (e.g., "Security:", "Performance:")
        if re.match(section_pattern, line):
            req_text = line.split(':')[0].strip()
            if req_text not in seen_texts and len(req_text) > 5:
                requirements.append({
                    "id": f"REQ-{req_id_counter:03d}",
                    "text": line[:200],  # Limit to 200 chars
                    "type": "SECTION_HEADER",
                    "confidence": 0.75
                })
                seen_texts.add(req_text)
                req_id_counter += 1

        # Split line into sentences
        sentences = re.split(r'[.!?]\s+', line)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:  # Lowered threshold from 20 to 15
                continue

            # Deduplicate
            if sentence in seen_texts:
                continue

            # 4️⃣ Check for modal verbs (strict requirements)
            if re.search(modal_pattern, sentence, re.IGNORECASE):
                requirements.append({
                    "id": f"REQ-{req_id_counter:03d}",
                    "text": sentence,
                    "type": "MODAL_VERB",
                    "confidence": 0.85
                })
                seen_texts.add(sentence)
                req_id_counter += 1

            # 5️⃣ Check for action verbs (feature/capability requirements)
            elif re.search(action_pattern, sentence, re.IGNORECASE):
                # Additional filter: avoid common prose (must contain system/user/feature/data)
                if any(keyword in sentence.lower() for keyword in ['system', 'user', 'feature', 'application', 'data', 'service', 'platform']):
                    requirements.append({
                        "id": f"REQ-{req_id_counter:03d}",
                        "text": sentence,
                        "type": "ACTION_VERB",
                        "confidence": 0.7
                    })
                    seen_texts.add(sentence)
                    req_id_counter += 1

            # 6️⃣ Check for bullet points or numbered lists
            elif re.match(r'^\s*[\-\*•○]\s+', sentence) or re.match(r'^\s*[0-9a-z]+[\.\)]\s+', sentence):
                # Lowered threshold from 20 to 15 characters
                if len(sentence) > 15:
                    requirements.append({
                        "id": f"REQ-{req_id_counter:03d}",
                        "text": sentence,
                        "type": "BULLET_POINT",
                        "confidence": 0.7
                    })
                    seen_texts.add(sentence)
                    req_id_counter += 1

    return requirements


def classify_chunk_labels(text: str) -> List[str]:
    """
    6️⃣ Classify chunk with multiple labels based on section headings and content
    
    Args:
        text: Chunk text content
        
    Returns:
        List of applicable chunk labels (can be multiple)
    """
    labels = []
    text_lower = text.lower()
    
    # Check for specific section headings and keywords
    if any(keyword in text_lower for keyword in ['acceptance criteria', 'acceptance test', 'ac:']):
        labels.append("ACCEPTANCE_CRITERIA")
    
    if any(keyword in text_lower for keyword in ['security', 'authentication', 'authorization', 'encryption']):
        labels.append("SECURITY")
    
    if any(keyword in text_lower for keyword in ['performance', 'scalability', 'load', 'response time']):
        labels.append("PERFORMANCE")
    
    if any(keyword in text_lower for keyword in ['compliance', 'regulation', 'gdpr', 'hipaa', 'sox', 'ccpa']):
        labels.append("COMPLIANCE")
    
    if any(keyword in text_lower for keyword in ['functional requirement', 'user story', 'feature']):
        labels.append("FUNCTIONAL_REQUIREMENT")
    
    if any(keyword in text_lower for keyword in ['technical', 'architecture', 'design']):
        labels.append("TECHNICAL")
    
    if any(keyword in text_lower for keyword in ['test', 'testing', 'qa']):
        labels.append("TEST")
    
    # If no specific labels found, mark as GENERAL
    if not labels:
        labels.append("GENERAL")
    
    return labels


def parse_document_ai_response(document: documentai.Document, document_name: str, processor_info: dict = None) -> dict:
    """
    Parse Document AI response and extract structured data with enhanced features
    
    Args:
        document: Document AI response document
        document_name: Name of the document
        processor_info: Optional processor metadata (name, location, id)
        
    Returns:
        Structured response with chunks, entities, and metadata
    """
    
    chunks = []
    all_entities = []
    compliance_entities = []
    requirement_entities = []
    
    # 2️⃣ Extract document-level entities OUTSIDE the page loop
    if hasattr(document, 'entities') and document.entities:
        for entity in document.entities:
            entity_text = entity.mention_text if hasattr(entity, 'mention_text') else ""
            if entity_text:
                # Get page number from entity's text anchor if available
                page_number = 1  # Default
                if hasattr(entity, 'page_anchor') and entity.page_anchor:
                    if hasattr(entity.page_anchor, 'page_refs') and entity.page_anchor.page_refs:
                        page_ref = entity.page_anchor.page_refs[0]
                        if hasattr(page_ref, 'page'):
                            page_number = page_ref.page + 1  # Convert 0-indexed to 1-indexed
                
                # Get text anchor indices
                text_anchor = None
                if hasattr(entity, 'text_anchor') and entity.text_anchor:
                    if hasattr(entity.text_anchor, 'text_segments') and entity.text_anchor.text_segments:
                        segment = entity.text_anchor.text_segments[0]
                        if hasattr(segment, 'start_index') and hasattr(segment, 'end_index'):
                            text_anchor = {
                                "start": segment.start_index,
                                "end": segment.end_index
                            }
                
                entity_data = {
                    "id": entity.id if hasattr(entity, 'id') and entity.id else f"entity_{len(all_entities) + 1}",
                    "text": entity_text,
                    "confidence": entity.confidence if hasattr(entity, 'confidence') else 0.0,
                    "page_number": page_number,
                    "type": entity.type_ if hasattr(entity, 'type_') and entity.type_ else "UNKNOWN"
                }
                
                # 5️⃣ Add text_anchor if available
                if text_anchor:
                    entity_data["text_anchor"] = text_anchor
                
                all_entities.append(entity_data)
                
                # Categorize entities
                entity_type = entity_data["type"]
                if entity_type in ["COMPLIANCE", "REGULATION", "STANDARD"]:
                    compliance_entities.append(entity_data)
                elif entity_type in ["REQUIREMENT", "FUNCTIONAL_REQUIREMENT"]:
                    requirement_entities.append(entity_data)
    
    # Extract text chunks from pages
    for page_num, page in enumerate(document.pages, 1):
        page_text = ""
        page_start_index = None
        page_end_index = None
        page_bounding_box = None
        
        # Extract text from page - handle different text extraction methods
        if hasattr(page, 'blocks') and page.blocks:
            # Extract text from blocks with real bounding boxes
            for block in page.blocks:
                if hasattr(block, 'layout') and block.layout:
                    # 3️⃣ Get real bounding box
                    if not page_bounding_box and block.layout:
                        page_bounding_box = get_bounding_poly(block.layout)
                    
                    if hasattr(block.layout, 'text_anchor') and block.layout.text_anchor:
                        if hasattr(block.layout.text_anchor, 'text_segments'):
                            for segment in block.layout.text_anchor.text_segments:
                                if segment.start_index is not None and segment.end_index is not None:
                                    # 5️⃣ Track text anchor indices
                                    if page_start_index is None:
                                        page_start_index = segment.start_index
                                    page_end_index = segment.end_index
                                    page_text += document.text[segment.start_index:segment.end_index] + "\n"
        
        # Fallback: extract text from paragraphs if blocks don't exist
        if not page_text and hasattr(page, 'paragraphs') and page.paragraphs:
            for paragraph in page.paragraphs:
                if hasattr(paragraph, 'layout') and paragraph.layout:
                    # 3️⃣ Get real bounding box
                    if not page_bounding_box:
                        page_bounding_box = get_bounding_poly(paragraph.layout)
                    
                    if hasattr(paragraph.layout, 'text_anchor') and paragraph.layout.text_anchor:
                        if hasattr(paragraph.layout.text_anchor, 'text_segments'):
                            for segment in paragraph.layout.text_anchor.text_segments:
                                if segment.start_index is not None and segment.end_index is not None:
                                    # 5️⃣ Track text anchor indices
                                    if page_start_index is None:
                                        page_start_index = segment.start_index
                                    page_end_index = segment.end_index
                                    page_text += document.text[segment.start_index:segment.end_index] + "\n"
        
        # Create chunks from page content if text exists
        if page_text.strip():
            # Get entities for this specific page
            page_entities = [e for e in all_entities if e.get("page_number") == page_num]
            
            # 6️⃣ Classify chunk with multiple labels
            chunk_labels = classify_chunk_labels(page_text)
            
            # 2️⃣ Detect compliance standards using regex
            detected_compliance = detect_compliance_standards(page_text)
            
            # 3️⃣ Detect requirements using rule-based detection
            detected_requirements = detect_requirements(page_text)
            
            chunk_data = {
                "chunk_id": f"chunk_{page_num:03d}",
                "labels": chunk_labels,  # 6️⃣ Multiple labels instead of single chunk_type
                "page_number": page_num,
                "text": page_text.strip(),
                "confidence": sum(e.get("confidence", 0) for e in page_entities) / len(page_entities) if page_entities else 0.9
            }
            
            # 5️⃣ Add text_anchor for chunk
            if page_start_index is not None and page_end_index is not None:
                chunk_data["text_anchor"] = {
                    "start": page_start_index,
                    "end": page_end_index
                }
            
            # 3️⃣ Add real bounding box if available
            if page_bounding_box:
                chunk_data["bounding_box"] = page_bounding_box
            
            # 2️⃣ Add detected compliance standards
            if detected_compliance:
                chunk_data["detected_compliance"] = detected_compliance
            
            # 3️⃣ Add detected requirements
            if detected_requirements:
                chunk_data["detected_requirements"] = detected_requirements
            
            # 4️⃣ Only add entity arrays if they have content (drop empty arrays)
            req_entities = [e for e in page_entities if e["type"] in ["REQUIREMENT", "FUNCTIONAL_REQUIREMENT"]]
            comp_entities = [e for e in page_entities if e["type"] in ["COMPLIANCE", "REGULATION", "STANDARD"]]
            
            if req_entities:
                chunk_data["requirement_entities"] = req_entities
            if comp_entities:
                chunk_data["compliance_entities"] = comp_entities
            
            chunk_data["source"] = document_name
            chunks.append(chunk_data)
    
    # Calculate base metadata
    total_pages = len(document.pages) if hasattr(document, 'pages') else 0
    total_chunks = len(chunks)
    text_length = len(document.text) if hasattr(document, 'text') and document.text else 0
    
    # 1️⃣ Count detected requirements and compliance from chunks
    total_detected_requirements = len(requirement_entities)
    total_detected_compliance = len(compliance_entities)
    
    # Add rule-based detections from chunks
    for chunk in chunks:
        if "detected_requirements" in chunk:
            total_detected_requirements += len(chunk["detected_requirements"])
        if "detected_compliance" in chunk:
            total_detected_compliance += len(chunk["detected_compliance"])
    
    # Total entities = requirements + compliance only
    total_detected_entities = total_detected_requirements + total_detected_compliance
    
    # 2️⃣ Build enhanced traceability edges (requirement → compliance) with normalized relationships
    edges = []
    edge_id_counter = 1
    
    # Link entity-based requirements to entity-based compliance
    for req_entity in requirement_entities:
        req_id = req_entity.get("id")
        req_page = req_entity.get("page_number")
        
        # Find compliance entities on the same page
        for comp_entity in compliance_entities:
            comp_page = comp_entity.get("page_number")
            
            # Link if on same page
            if req_page == comp_page:
                edges.append({
                    "edge_id": f"edge_{edge_id_counter:03d}",
                    "source": req_id,
                    "source_type": "requirement",              # 2️⃣ Normalized type
                    "target": comp_entity.get("id"),
                    "target_type": "compliance",               # 2️⃣ Normalized type
                    "relationship": "GOVERNED_BY",
                    "relationship_type": "entity_to_entity",   # 2️⃣ Relationship type
                    "confidence": 0.8,
                    "page": req_page
                })
                edge_id_counter += 1
    
    # Link detected requirements to detected compliance on same page
    for chunk in chunks:
        chunk_page = chunk.get("page_number")
        detected_reqs = chunk.get("detected_requirements", [])
        detected_comps = chunk.get("detected_compliance", [])
        
        if detected_reqs and detected_comps:
            for req in detected_reqs:
                for comp in detected_comps:
                    edges.append({
                        "edge_id": f"edge_{edge_id_counter:03d}",
                        "source": req.get("id"),
                        "source_type": "detected_requirement",  # 2️⃣ Normalized type
                        "target": comp.get("canonical_id"),
                        "target_type": "compliance_standard",   # 2️⃣ Normalized type
                        "relationship": "REQUIRES_COMPLIANCE",
                        "relationship_type": "rule_based",      # 2️⃣ Relationship type
                        "confidence": 0.7,
                        "page": chunk_page
                    })
                    edge_id_counter += 1
    
    # 3️⃣ Add trace_links to each chunk for same-page edges
    for chunk in chunks:
        chunk_page = chunk.get("page_number")
        # Find all edges for this page
        page_edges = [e for e in edges if e.get("page") == chunk_page]
        if page_edges:
            chunk["trace_links"] = page_edges
    
    # Build final response
    response = {
        "status": "success",
        "agent": "Document AI",
        "source_document": {
            "name": document_name,
            "id": f"doc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")
        },
        "chunks": chunks,
        "edges": edges,  # 2️⃣ Enhanced traceability edges with normalized types
        "summary": {
            "total_pages": total_pages,
            "total_chunks": total_chunks,
            "total_detected_entities": total_detected_entities,
            "total_detected_requirements": total_detected_requirements,
            "total_detected_compliance": total_detected_compliance,
            "text_length": text_length,
            "has_entities": total_detected_entities > 0,
            "compliance_standards_found": total_detected_compliance,  # 1️⃣ Use total count
            "requirements_found": total_detected_requirements,        # 1️⃣ Use total count
            "kg_ready": True,                                         # 4️⃣ Graph ingestion readiness
            "total_edges": len(edges)
        }
    }
    
    # Include processor metadata if available
    if processor_info:
        response["processor"] = processor_info
    
    return response
