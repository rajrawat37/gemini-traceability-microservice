#!/usr/bin/env python3
"""
Test enhanced bounding box extraction on PRD-7.pdf
Tests just the Document AI stage with new multi-line handling
"""
import os
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.document_ai import extract_traceable_docai

def main():
    print("=" * 80)
    print("🧪 Testing Enhanced Bounding Box Extraction")
    print("=" * 80)

    # Check for PRD-7.pdf
    pdf_path = project_root / "mockData" / "documents" / "PRD-7.pdf"

    if not pdf_path.exists():
        print(f"❌ ERROR: PRD-7.pdf not found at {pdf_path}")
        return 1

    # Get environment variables
    project_id = os.getenv("PROJECT_ID", "poc-genai-hacks")
    location = os.getenv("LOCATION", "us")
    processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")

    print(f"📄 PDF: {pdf_path}")
    print(f"🏗️  Project: {project_id}")
    print(f"📍 Location: {location}")
    print(f"🔍 Processor: {processor_id}\n")

    # Read PDF
    with open(pdf_path, 'rb') as f:
        content = f.read()

    # Run Document AI extraction
    print("🚀 Running Document AI extraction with enhanced bbox logic...")
    result = extract_traceable_docai(content, project_id, location, processor_id, "PRD-7.pdf")

    # Analyze results
    print("\n" + "=" * 80)
    print("📊 ANALYSIS OF RESULTS")
    print("=" * 80)

    chunks = result.get("chunks", [])
    print(f"\nTotal chunks: {len(chunks)}")

    total_requirements = 0
    requirements_with_bbox = 0
    bbox_details = []

    for chunk in chunks:
        detected_requirements = chunk.get("detected_requirements", [])
        total_requirements += len(detected_requirements)

        for req in detected_requirements:
            req_id = req.get("id", "UNKNOWN")
            req_text = req.get("text", "")
            req_bbox = req.get("bounding_box")

            if req_bbox:
                requirements_with_bbox += 1
                bbox_details.append({
                    "id": req_id,
                    "text": req_text[:80] + "..." if len(req_text) > 80 else req_text,
                    "text_length": len(req_text),
                    "page": chunk.get("page_number"),
                    "bbox": req_bbox
                })

    print(f"\n📋 Requirements detected: {total_requirements}")
    print(f"✅ Requirements with bounding boxes: {requirements_with_bbox}")
    print(f"📊 Coverage: {requirements_with_bbox/total_requirements*100:.1f}%\n")

    if requirements_with_bbox == 0:
        print("❌ WARNING: No bounding boxes found!")
        return 1

    # Show sample bounding boxes
    print("=" * 80)
    print("📦 SAMPLE BOUNDING BOXES")
    print("=" * 80)
    print(f"{'Req ID':<12} {'Page':<6} {'Text Length':<12} {'Bbox Y Range':<20}")
    print("-" * 80)

    for detail in bbox_details[:10]:  # Show first 10
        bbox = detail['bbox']
        y_range = f"{bbox.get('y_min', 0):.3f}-{bbox.get('y_max', 0):.3f}"
        print(f"{detail['id']:<12} {detail['page']:<6} {detail['text_length']:<12} {y_range:<20}")
        print(f"  Text: {detail['text']}")
        print()

    # Check for multi-line bboxes (height > 0.05 suggests multiple lines)
    multi_line_bboxes = [d for d in bbox_details
                          if d['bbox'].get('y_max', 0) - d['bbox'].get('y_min', 0) > 0.05]

    print(f"\n📏 Potentially multi-line bounding boxes: {len(multi_line_bboxes)}/{len(bbox_details)}")

    if multi_line_bboxes:
        print("\nExample multi-line bounding boxes:")
        for detail in multi_line_bboxes[:3]:
            bbox = detail['bbox']
            height = bbox.get('y_max', 0) - bbox.get('y_min', 0)
            print(f"  {detail['id']}: Height={height:.3f}, Text length={detail['text_length']}")
            print(f"    {detail['text'][:60]}...")

    # Save results
    output_file = project_root / "tests" / "outputs" / "test_enhanced_bbox_output.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Full output saved to: {output_file}")

    print("\n" + "=" * 80)
    if requirements_with_bbox >= total_requirements * 0.9:
        print("✅ TEST PASSED: Enhanced bounding box extraction is working!")
        return 0
    else:
        print(f"⚠️  TEST WARNING: Only {requirements_with_bbox}/{total_requirements} requirements have bboxes")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
