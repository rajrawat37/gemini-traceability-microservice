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
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from google.cloud import documentai
from google.cloud.documentai_v1 import DocumentProcessorServiceClient
from google.protobuf.json_format import MessageToJson
from .mock_data_loader import load_document_ai_mock


# ==================== CONFIGURATION ====================

# Context expansion configuration (can be overridden via environment variables)
ENABLE_CONTEXT_EXPANSION = os.getenv('ENABLE_CONTEXT_EXPANSION', 'true').lower() == 'true'
MAX_EXPANSION_SENTENCES = int(os.getenv('MAX_EXPANSION_SENTENCES', '3'))
MAX_EXPANSION_CHARS = int(os.getenv('MAX_EXPANSION_CHARS', '300'))


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
        # Convert proto-plus message to raw protobuf
        document = result.document

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
        'ISO27001': {
            'patterns': [
                r'\bISO\s*27001\b',
                r'\bISO/IEC\s*27001\b',
                r'information security management'
            ],
            'canonical_id': 'ISO27001:2013',
            'name': 'ISO27001'
        },
        'ISO9001': {
            'patterns': [
                r'\bISO\s*9001\b',
                r'\bISO/IEC\s*9001\b',
                r'quality management system',
                r'QMS.*ISO\s*9001'
            ],
            'canonical_id': 'ISO9001:2015',
            'name': 'ISO 9001'
        },
        'ISO13485': {
            'patterns': [
                r'\bISO\s*13485\b',
                r'\bISO/IEC\s*13485\b',
                r'medical devices.*quality management',
                r'QMS.*medical devices'
            ],
            'canonical_id': 'ISO13485:2016',
            'name': 'ISO 13485'
        },
        'IEC62304': {
            'patterns': [
                r'\bIEC\s*62304\b',
                r'\bIEC-62304\b',
                r'medical device software',
                r'software life cycle.*medical device'
            ],
            'canonical_id': 'IEC62304:2006',
            'name': 'IEC 62304'
        },
        'FDA': {
            'patterns': [
                r'\bFDA\b',
                r'Food and Drug Administration',
                r'FDA\s+approval',
                r'FDA\s+regulation',
                r'FDA\s+compliant'
            ],
            'canonical_id': 'FDA:US-FDA',
            'name': 'FDA'
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


# ==================== REQUIREMENT CONTEXT EXPANSION FUNCTIONS ====================

def smart_split_sentences(text: str) -> List[Dict]:
    """
    Split text into sentences with position metadata

    Args:
        text: Input text to split

    Returns:
        List of dicts with keys:
        - text: sentence text
        - start_pos: character position in original text
        - end_pos: character position in original text
    """
    import re

    sentences = []
    # Split on sentence-ending punctuation followed by whitespace
    pattern = r'([.!?]+\s+)'
    parts = re.split(pattern, text)

    current_pos = 0
    current_sentence = ""

    for i, part in enumerate(parts):
        if re.match(r'[.!?]+\s+', part):
            # This is sentence-ending punctuation
            current_sentence += part.rstrip()  # Keep punctuation, remove trailing space
            sentences.append({
                "text": current_sentence.strip(),
                "start_pos": current_pos,
                "end_pos": current_pos + len(current_sentence)
            })
            current_pos += len(current_sentence) + 1  # +1 for the space
            current_sentence = ""
        else:
            # This is sentence content
            current_sentence += part

    # Add last sentence if any
    if current_sentence.strip():
        sentences.append({
            "text": current_sentence.strip(),
            "start_pos": current_pos,
            "end_pos": current_pos + len(current_sentence)
        })

    return sentences


def is_continuation_sentence(current: str, next_sent: str) -> bool:
    """
    Determine if next_sent continues the current requirement

    Indicators that next sentence continues:
    - Starts with lowercase (likely mid-thought)
    - Starts with conjunction (and, or, but)
    - Starts with pronoun (It, This, These, They, That)
    - Starts with adverb (Additionally, Furthermore, Also)
    - No section markers (numbers, bullets)

    Args:
        current: Current sentence
        next_sent: Next sentence to check

    Returns:
        True if next sentence likely continues same requirement
    """
    if not next_sent:
        return False

    next_sent = next_sent.strip()
    if not next_sent:
        return False

    # IMPORTANT: Check section breaks FIRST (higher priority)
    # Section breaks definitely mean NOT a continuation
    section_break_patterns = [
        r'^\d+\.',  # "1. ", "2. "
        r'^[•\-\*○●]',  # Bullet points
        r'^[A-Z][a-zA-Z\s&-]{2,}:',  # "Security:", "Features:" (2+ chars before colon)
        r'^\([a-z0-9]+\)',  # "(a)", "(1)"
        r'^[IVX]+\.',  # Roman numerals "I.", "II."
    ]

    for pattern in section_break_patterns:
        if re.match(pattern, next_sent):
            return False  # Definitely a new section

    # Then check for continuation indicators
    continuation_patterns = [
        r'^(and|or|but|yet|so)\s+',  # Conjunctions
        r'^(it|this|these|they|that|which|who)\s+',  # Pronouns
        r'^(additionally|furthermore|also|moreover|however|therefore)\s*[,:]?\s+',  # Adverbs
        r'^[a-z]',  # Starts with lowercase (likely continuation)
    ]

    for pattern in continuation_patterns:
        if re.match(pattern, next_sent, re.IGNORECASE):
            return True

    return False


def is_complete_thought(text: str) -> bool:
    """
    Check if text represents a complete thought/requirement

    Complete thought indicators:
    - Ends with proper punctuation (. ! ?)
    - Has minimum length (20+ characters)
    - Has multiple words (3+)

    Args:
        text: Text to check

    Returns:
        True if text appears to be a complete thought
    """
    if not text or len(text.strip()) < 20:
        return False

    text_stripped = text.strip()

    # Check ending punctuation
    if not re.search(r'[.!?]$', text_stripped):
        return False

    # Check has multiple words
    words = text_stripped.split()
    if len(words) < 3:
        return False

    return True


def expand_requirement_context(
    initial_sentence: str,
    full_line_text: str,
    max_sentences: int = 3,
    max_chars: int = 300
) -> str:
    """
    🚀 Expand a requirement sentence to capture full multi-sentence context

    Strategy:
    1. Find initial sentence position in full text
    2. Look ahead for continuation sentences
    3. Stop when:
       - Hit section break
       - Hit unrelated content
       - Reach max sentences/chars
       - Complete thought detected with sufficient length

    Args:
        initial_sentence: The single sentence that triggered requirement detection
        full_line_text: The full text of the line/paragraph containing the sentence
        max_sentences: Maximum number of sentences to include (default: 3)
        max_chars: Maximum total characters (default: 300)

    Returns:
        Expanded requirement text (may be same as initial if no expansion needed)

    Examples:
        >>> expand_requirement_context(
        ...     "The system shall authenticate users",
        ...     "The system shall authenticate users. It must use multi-factor authentication."
        ... )
        'The system shall authenticate users. It must use multi-factor authentication.'

        >>> expand_requirement_context(
        ...     "The application must encrypt data",
        ...     "Security: The application must encrypt data. Performance: Fast loading."
        ... )
        'The application must encrypt data.'  # Stops at section break
    """
    if not initial_sentence or not full_line_text:
        return initial_sentence

    # Normalize
    initial_sentence = initial_sentence.strip()
    full_line_text = full_line_text.strip()

    # If initial sentence is already complete and long enough, return it
    if is_complete_thought(initial_sentence) and len(initial_sentence) > 50:
        return initial_sentence

    # Split full text into sentences with positions
    sentences = smart_split_sentences(full_line_text)

    if not sentences:
        return initial_sentence

    # Find the initial sentence in the list (fuzzy match)
    initial_idx = None
    initial_normalized = ' '.join(initial_sentence.lower().split())

    for idx, sent_obj in enumerate(sentences):
        sent_normalized = ' '.join(sent_obj["text"].lower().split())
        # Fuzzy match - check if initial is contained in sentence
        if initial_normalized[:50] in sent_normalized[:60] or sent_normalized[:50] in initial_normalized[:60]:
            initial_idx = idx
            break

    if initial_idx is None:
        # Couldn't find initial sentence, return as-is
        return initial_sentence

    # Build expanded requirement
    expanded_sentences = [sentences[initial_idx]["text"]]
    current_length = len(expanded_sentences[0])

    # Look ahead for continuation sentences
    for i in range(1, max_sentences):
        next_idx = initial_idx + i

        if next_idx >= len(sentences):
            break  # No more sentences

        next_sent = sentences[next_idx]["text"]
        current_sent = expanded_sentences[-1]

        # Check if this is a continuation
        if not is_continuation_sentence(current_sent, next_sent):
            # Not a continuation, stop here
            break

        # Check length limit
        if current_length + len(next_sent) + 1 > max_chars:  # +1 for space
            # Would exceed max length, stop
            break

        # Add the continuation sentence
        expanded_sentences.append(next_sent)
        current_length += len(next_sent) + 1

        # Check if we now have a complete thought with good length
        combined = ' '.join(expanded_sentences)
        if is_complete_thought(combined) and len(combined) > 80:
            # Good stopping point - have a complete, substantial thought
            break

    # Join and return
    expanded_text = ' '.join(expanded_sentences)

    # Clean up extra spaces
    expanded_text = re.sub(r'\s+', ' ', expanded_text).strip()

    return expanded_text


# ==================== MULTI-LINE REQUIREMENT HELPER FUNCTIONS ====================

def is_paragraph_element(element) -> bool:
    """Check if a Document AI element is a paragraph"""
    if not element or not hasattr(element, '__class__'):
        return False
    class_name = element.__class__.__name__.lower()
    return 'paragraph' in class_name


def is_line_element(element) -> bool:
    """Check if a Document AI element is a line"""
    if not element or not hasattr(element, '__class__'):
        return False
    class_name = element.__class__.__name__.lower()
    return 'line' in class_name and 'paragraph' not in class_name


def extract_element_text(element, full_document_text: str) -> str:
    """Extract text from any Document AI layout element"""
    if not element or not hasattr(element, 'layout'):
        return ""

    element_text = ""
    if hasattr(element.layout, 'text_anchor') and element.layout.text_anchor:
        if hasattr(element.layout.text_anchor, 'text_segments'):
            for segment in element.layout.text_anchor.text_segments:
                if segment.start_index is not None and segment.end_index is not None:
                    element_text += full_document_text[segment.start_index:segment.end_index]

    return element_text


def calculate_text_overlap(text1: str, text2: str) -> float:
    """
    Calculate what percentage of text1 is contained in text2
    Returns value between 0.0 and 1.0
    """
    if not text1 or not text2:
        return 0.0

    # Normalize texts
    text1_normalized = ' '.join(text1.lower().split())
    text2_normalized = ' '.join(text2.lower().split())

    # Word-level overlap
    words1 = set(text1_normalized.split())
    words2 = set(text2_normalized.split())

    if not words1:
        return 0.0

    common_words = words1 & words2
    overlap = len(common_words) / len(words1)

    return overlap


def merge_bounding_boxes(bboxes: List[Dict]) -> Dict:
    """
    Merge multiple bounding boxes into one that encompasses all of them

    Args:
        bboxes: List of bounding box dicts with x_min, y_min, x_max, y_max

    Returns:
        Merged bounding box dict
    """
    if not bboxes:
        return {}

    # Filter out empty bboxes
    valid_bboxes = [b for b in bboxes if b and all(k in b for k in ['x_min', 'y_min', 'x_max', 'y_max'])]

    if not valid_bboxes:
        return {}

    return {
        "x_min": min(b["x_min"] for b in valid_bboxes),
        "y_min": min(b["y_min"] for b in valid_bboxes),
        "x_max": max(b["x_max"] for b in valid_bboxes),
        "y_max": max(b["y_max"] for b in valid_bboxes)
    }


# ==================== ENHANCED BOUNDING BOX FINDER ====================

def find_text_bounding_box(target_text: str, page_layout_elements: List, full_document_text: str) -> dict:
    """
    🚀 ENHANCED: Find bounding box for multi-line requirements using 3-tier strategy

    Strategy:
    1. TIER 1 (Paragraphs): Try paragraphs first - they often contain complete multi-line text
    2. TIER 2 (Multi-line merge): Find ALL matching lines and merge their bounding boxes
    3. TIER 3 (Fallback): Single element fuzzy match

    Args:
        target_text: The requirement text to find
        page_layout_elements: List of layout elements (tokens, paragraphs, lines) from Document AI
        full_document_text: The complete document text for text_anchor matching

    Returns:
        Bounding box dict or None if not found
    """
    if not target_text or not page_layout_elements:
        return None

    # Normalize target text for matching (lowercase, remove extra spaces)
    target_normalized = ' '.join(target_text.lower().split())
    target_words = set(target_normalized.split())

    # Separate elements by type for more efficient processing
    paragraphs = [el for el in page_layout_elements if is_paragraph_element(el)]
    lines = [el for el in page_layout_elements if is_line_element(el)]
    other_elements = [el for el in page_layout_elements
                      if not is_paragraph_element(el) and not is_line_element(el)]

    # ==================== TIER 1: Try Paragraphs First (FAST PATH) ====================
    # Paragraphs typically contain full multi-line text blocks
    for para in paragraphs:
        para_text = extract_element_text(para, full_document_text)
        if not para_text:
            continue

        para_normalized = ' '.join(para_text.lower().split())

        # Check if paragraph contains most of the requirement (≥70% overlap)
        overlap = calculate_text_overlap(target_normalized, para_normalized)
        if overlap >= 0.7:
            bbox = get_bounding_poly(para.layout)
            if bbox:
                return bbox

    # ==================== TIER 2: Merge Multiple Lines (ACCURATE PATH) ====================
    # If no paragraph match, find ALL lines that contain parts of the requirement
    # and merge their bounding boxes to capture the full multi-line text
    matching_lines = []

    for line in lines:
        line_text = extract_element_text(line, full_document_text)
        if not line_text:
            continue

        line_normalized = ' '.join(line_text.lower().split())
        line_words = set(line_normalized.split())

        # Calculate word overlap: how many requirement words are in this line?
        if not target_words:
            continue

        common_words = target_words & line_words
        word_overlap = len(common_words) / len(target_words)

        # Include line if it contains ≥20% of requirement words
        if word_overlap >= 0.2:
            matching_lines.append((line, word_overlap, line_text))

    # If we found multiple matching lines, merge their bounding boxes
    if matching_lines:
        # Sort by overlap score (highest first)
        matching_lines.sort(key=lambda x: x[1], reverse=True)

        # Take lines with significant overlap (≥20%)
        significant_lines = [line for line, score, text in matching_lines if score >= 0.2]

        if significant_lines:
            # Extract bounding boxes
            bboxes = []
            for line in significant_lines:
                bbox = get_bounding_poly(line.layout)
                if bbox:
                    bboxes.append(bbox)

            # Merge all bounding boxes into one
            if bboxes:
                merged_bbox = merge_bounding_boxes(bboxes)
                if merged_bbox:
                    return merged_bbox

    # ==================== TIER 3: Fallback - Single Element Match ====================
    # If tiers 1 and 2 didn't work, fall back to original fuzzy matching
    # This handles edge cases where the text might be in tokens or other elements
    all_elements = paragraphs + lines + other_elements

    for element in all_elements:
        if not hasattr(element, 'layout') or not element.layout:
            continue

        element_text = extract_element_text(element, full_document_text)
        if not element_text:
            continue

        element_normalized = ' '.join(element_text.lower().split())

        # Check if target text is contained in this element (fuzzy match)
        if target_normalized in element_normalized or element_normalized in target_normalized:
            bbox = get_bounding_poly(element.layout)
            if bbox:
                return bbox

    return None


def detect_requirements(text: str, page_layout_elements: List = None, full_document_text: str = None) -> List[Dict[str, Any]]:
    """
    3️⃣ ENHANCED rule-based requirement detection with multiple strategies + bounding boxes

    Detects requirements using:
    - Modal verbs (shall, must, should, will)
    - Key action verbs (provide, support, enable, allow, implement)
    - Bullet points and numbered lists
    - Section headers as high-level requirements
    - Feature/capability descriptions

    NEW: Extracts bounding boxes for each requirement by matching text to layout elements

    Args:
        text: Text to analyze
        page_layout_elements: Optional list of Document AI layout elements (paragraphs, lines, tokens) for bounding box extraction
        full_document_text: Optional full document text for text_anchor matching

    Returns:
        List of detected requirements with metadata and bounding boxes
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
                req_obj = {
                    "id": f"REQ-{req_id_counter:03d}",
                    "text": line[:200],  # Limit to 200 chars
                    "type": "SECTION_HEADER",
                    "confidence": 0.75
                }

                # 🚀 NEW: Extract bounding box for this requirement
                if page_layout_elements and full_document_text:
                    bbox = find_text_bounding_box(line, page_layout_elements, full_document_text)
                    if bbox:
                        req_obj["bounding_box"] = bbox

                requirements.append(req_obj)
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
                # 🚀 NEW: Expand context if enabled
                if ENABLE_CONTEXT_EXPANSION:
                    expanded_text = expand_requirement_context(
                        sentence,
                        text,  # Pass full page text as context (not just line)
                        max_sentences=MAX_EXPANSION_SENTENCES,
                        max_chars=MAX_EXPANSION_CHARS
                    )
                else:
                    expanded_text = sentence

                req_obj = {
                    "id": f"REQ-{req_id_counter:03d}",
                    "text": expanded_text,  # 🔥 Use expanded text
                    "type": "MODAL_VERB",
                    "confidence": 0.85
                }

                # 🚀 NEW: Extract bounding box for EXPANDED requirement
                if page_layout_elements and full_document_text:
                    bbox = find_text_bounding_box(expanded_text, page_layout_elements, full_document_text)
                    if bbox:
                        req_obj["bounding_box"] = bbox

                requirements.append(req_obj)
                seen_texts.add(expanded_text)  # Deduplicate on expanded text
                req_id_counter += 1

            # 5️⃣ Check for action verbs (feature/capability requirements)
            elif re.search(action_pattern, sentence, re.IGNORECASE):
                # Additional filter: avoid common prose (must contain system/user/feature/data)
                if any(keyword in sentence.lower() for keyword in ['system', 'user', 'feature', 'application', 'data', 'service', 'platform']):
                    # 🚀 NEW: Expand context if enabled
                    if ENABLE_CONTEXT_EXPANSION:
                        expanded_text = expand_requirement_context(
                            sentence,
                            text,  # Pass full page text as context (not just line)
                            max_sentences=MAX_EXPANSION_SENTENCES,
                            max_chars=MAX_EXPANSION_CHARS
                        )
                    else:
                        expanded_text = sentence

                    req_obj = {
                        "id": f"REQ-{req_id_counter:03d}",
                        "text": expanded_text,  # 🔥 Use expanded text
                        "type": "ACTION_VERB",
                        "confidence": 0.7
                    }

                    # 🚀 NEW: Extract bounding box for EXPANDED requirement
                    if page_layout_elements and full_document_text:
                        bbox = find_text_bounding_box(expanded_text, page_layout_elements, full_document_text)
                        if bbox:
                            req_obj["bounding_box"] = bbox

                    requirements.append(req_obj)
                    seen_texts.add(expanded_text)  # Deduplicate on expanded text
                    req_id_counter += 1

            # 6️⃣ Check for bullet points or numbered lists
            elif re.match(r'^\s*[\-\*•○]\s+', sentence) or re.match(r'^\s*[0-9a-z]+[\.\)]\s+', sentence):
                # Lowered threshold from 20 to 15 characters
                if len(sentence) > 15:
                    # 🚀 NEW: Expand context if enabled
                    if ENABLE_CONTEXT_EXPANSION:
                        expanded_text = expand_requirement_context(
                            sentence,
                            text,  # Pass full page text as context (not just line)
                            max_sentences=MAX_EXPANSION_SENTENCES,
                            max_chars=MAX_EXPANSION_CHARS
                        )
                    else:
                        expanded_text = sentence

                    req_obj = {
                        "id": f"REQ-{req_id_counter:03d}",
                        "text": expanded_text,  # 🔥 Use expanded text
                        "type": "BULLET_POINT",
                        "confidence": 0.7
                    }

                    # 🚀 NEW: Extract bounding box for EXPANDED requirement
                    if page_layout_elements and full_document_text:
                        bbox = find_text_bounding_box(expanded_text, page_layout_elements, full_document_text)
                        if bbox:
                            req_obj["bounding_box"] = bbox

                    requirements.append(req_obj)
                    seen_texts.add(expanded_text)  # Deduplicate on expanded text
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

            # 2️⃣ Detect compliance standards using regex (REAL detection on extracted text)
            detected_compliance = detect_compliance_standards(page_text)
            
            # Log compliance detection results for debugging
            if detected_compliance:
                print(f"📋 Page {page_num}: Regex detected {len(detected_compliance)} compliance standards: {[c.get('name') for c in detected_compliance]}")
            
            # 3️⃣ Detect requirements using rule-based detection WITH bounding boxes
            # Collect layout elements from this page (paragraphs, lines, tokens)
            page_layout_elements = []
            if hasattr(page, 'paragraphs') and page.paragraphs:
                page_layout_elements.extend(page.paragraphs)
            if hasattr(page, 'lines') and page.lines:
                page_layout_elements.extend(page.lines)
            if hasattr(page, 'tokens') and page.tokens:
                page_layout_elements.extend(page.tokens)

            detected_requirements = detect_requirements(
                page_text,
                page_layout_elements=page_layout_elements,
                full_document_text=document.text
            )
            
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
            
            # Log Document AI entity-based compliance (if any)
            if comp_entities:
                print(f"📋 Page {page_num}: Document AI API detected {len(comp_entities)} compliance entities: {[e.get('text', e.get('id', 'Unknown')) for e in comp_entities]}")
            
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
    regex_compliance_count = 0
    for chunk in chunks:
        if "detected_requirements" in chunk:
            total_detected_requirements += len(chunk["detected_requirements"])
        if "detected_compliance" in chunk:
            total_detected_compliance += len(chunk["detected_compliance"])
            regex_compliance_count += len(chunk["detected_compliance"])
    
    # Log compliance detection summary
    print(f"\n📊 COMPLIANCE DETECTION SUMMARY:")
    print(f"   - From Document AI API entities: {len(compliance_entities)}")
    print(f"   - From regex patterns (on extracted text): {regex_compliance_count}")
    print(f"   - TOTAL compliance standards found: {total_detected_compliance}")
    print(f"   ⚠️  Note: Regex-based detection is REAL (scans actual document text)")
    if len(compliance_entities) == 0 and regex_compliance_count > 0:
        print(f"   ℹ️  All compliance found via regex patterns (Document AI didn't detect any)")
    
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
