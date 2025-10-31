#!/usr/bin/env python3
"""
Quick test of the enhanced bounding box function
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.document_ai import (
    is_paragraph_element,
    is_line_element,
    extract_element_text,
    calculate_text_overlap,
    merge_bounding_boxes
)

def test_helper_functions():
    """Test the helper functions"""
    print("🧪 Testing helper functions...")

    # Test calculate_text_overlap
    text1 = "The system shall authenticate users"
    text2 = "The system shall authenticate users with passwords"
    overlap = calculate_text_overlap(text1, text2)
    print(f"✓ Text overlap: {overlap:.2%} (expected ~83%)")
    assert overlap > 0.8, f"Overlap too low: {overlap}"

    # Test merge_bounding_boxes
    bbox1 = {"x_min": 0.1, "y_min": 0.2, "x_max": 0.5, "y_max": 0.3}
    bbox2 = {"x_min": 0.1, "y_min": 0.3, "x_max": 0.5, "y_max": 0.4}
    merged = merge_bounding_boxes([bbox1, bbox2])
    print(f"✓ Merged bbox: {merged}")
    assert merged["y_min"] == 0.2 and merged["y_max"] == 0.4, "Merge failed"

    print("✅ All helper function tests passed!\n")

if __name__ == "__main__":
    try:
        test_helper_functions()
        print("✅ Quick test completed successfully!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
