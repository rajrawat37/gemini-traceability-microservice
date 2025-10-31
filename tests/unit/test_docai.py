#!/usr/bin/env python3
"""
Test Document AI Integration
Simple script to test Document AI API integration with base64 encoding
Matches Node.js implementation
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.document_ai import extract_traceable_docai


def test_document_ai():
    """Test Document AI integration with a sample PDF"""
    
    print("🧪 Testing Document AI Integration (Python → matching Node.js)")
    print("=" * 70)
    
    # Check environment variables (matching Node.js env vars)
    project_id = os.getenv("PROJECT_ID", "401328495550")
    location = os.getenv("LOCATION", "us")
    processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")
    use_mock = os.getenv("USE_MOCK_DOCAI", "false").lower() == "true"
    
    print(f"📋 Configuration:")
    print(f"   Project ID: {project_id}")
    print(f"   Location: {location}")
    print(f"   Processor ID: {processor_id}")
    print(f"   Mock Mode: {use_mock}")
    print(f"   Processor Name: projects/{project_id}/locations/{location}/processors/{processor_id}")
    print()
    
    # Test with sample PDF
    sample_pdf_path = project_root / "mockData" / "documents" / "PRD-3.pdf"
    
    if not sample_pdf_path.exists():
        print(f"❌ Sample PDF not found at {sample_pdf_path}")
        return False
    
    try:
        # Read the PDF file
        with open(sample_pdf_path, 'rb') as f:
            content = f.read()
        
        print(f"📄 Processing: {sample_pdf_path.name}")
        print(f"📊 File info:")
        print(f"   Name: {sample_pdf_path.name}")
        print(f"   Type: application/pdf")
        print(f"   Size: {len(content)} bytes")
        print()
        
        # Process with Document AI (matching Node.js call)
        print(f"🔄 Calling Document AI API...")
        result = extract_traceable_docai(
            content=content,
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            document_name=sample_pdf_path.name,
            use_mock=use_mock
        )
        
        # Display results (matching Node.js response structure)
        print("\n" + "=" * 70)
        print("✅ Document AI Processing Results:")
        print("=" * 70)
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Agent: {result.get('agent', 'unknown')}")
        
        source_doc = result.get('source_document', {})
        print(f"   Document: {source_doc.get('name', 'unknown')}")
        print(f"   Document ID: {source_doc.get('id', 'unknown')}")
        print(f"   Processed At: {source_doc.get('processed_at', 'unknown')}")
        
        metadata = result.get('metadata', {})
        print(f"\n📊 Metadata:")
        print(f"   Pages: {metadata.get('total_pages', 0)}")
        print(f"   Chunks: {metadata.get('total_chunks', 0)}")
        print(f"   Entities: {metadata.get('total_detected_entities', 0)}")
        print(f"   Text Length: {metadata.get('text_length', 0)} characters")
        print(f"   Has Entities: {metadata.get('has_entities', False)}")
        print(f"   Requirements Found: {metadata.get('requirements_found', 0)}")
        print(f"   Compliance Standards: {metadata.get('compliance_standards_found', 0)}")
        
        chunks = result.get('chunks', [])
        if chunks:
            print(f"\n📝 Sample Chunk (First Page):")
            print("   " + "-" * 66)
            sample_chunk = chunks[0]
            print(f"   Chunk ID: {sample_chunk.get('chunk_id', 'unknown')}")
            print(f"   Type: {sample_chunk.get('chunk_type', 'unknown')}")
            print(f"   Page: {sample_chunk.get('page_number', 'unknown')}")
            print(f"   Confidence: {sample_chunk.get('confidence', 0):.2f}")
            print(f"   Text Preview: {sample_chunk.get('text', '')[:150]}...")
            
            req_entities = sample_chunk.get('requirement_entities', [])
            comp_entities = sample_chunk.get('compliance_entities', [])
            print(f"   Requirement Entities: {len(req_entities)}")
            print(f"   Compliance Entities: {len(comp_entities)}")
        
        print("\n" + "=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ Error processing document: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Document AI Integration Test (Python)")
    print("   Matching Node.js implementation")
    print("=" * 70)
    print()
    
    success = test_document_ai()
    
    print()
    print("=" * 70)
    if success:
        print("✅ Test completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Test via API: python api_server_modular.py")
        print("   2. Call endpoint: POST http://localhost:8080/extract-document")
        print("   3. Check logs for detailed processing information")
    else:
        print("❌ Test failed!")
        print()
        print("💡 Troubleshooting:")
        print("1. Check your Google Cloud credentials:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        print("2. Verify Document AI API is enabled in your project")
        print("3. Ensure processor ID is correct")
        print("4. Try setting USE_MOCK_DOCAI=true for testing with mock data")
        print("5. Check network connectivity to Google Cloud")
    
    sys.exit(0 if success else 1)
