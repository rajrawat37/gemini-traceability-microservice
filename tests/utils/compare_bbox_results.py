#!/usr/bin/env python3
"""
Compare bounding box results: Old extraction vs Enhanced extraction
"""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent

def analyze_bboxes(file_path):
    """Analyze bounding boxes from output file"""
    with open(file_path) as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    total_reqs = 0
    with_bbox = 0
    bbox_sizes = []

    for chunk in chunks:
        reqs = chunk.get("detected_requirements", [])
        total_reqs += len(reqs)

        for req in reqs:
            if "bounding_box" in req:
                with_bbox += 1
                bbox = req["bounding_box"]
                height = bbox.get("y_max", 0) - bbox.get("y_min", 0)
                width = bbox.get("x_max", 0) - bbox.get("x_min", 0)
                bbox_sizes.append({
                    "id": req.get("id"),
                    "height": height,
                    "width": width,
                    "text_len": len(req.get("text", ""))
                })

    return {
        "total": total_reqs,
        "with_bbox": with_bbox,
        "sizes": bbox_sizes
    }

def main():
    print("=" * 80)
    print("📊 BOUNDING BOX COMPARISON: Before vs After Enhancement")
    print("=" * 80)

    # Check if enhanced output exists
    enhanced_file = project_root / "tests" / "outputs" / "test_enhanced_bbox_output.json"
    if not enhanced_file.exists():
        print(f"❌ Enhanced output not found: {enhanced_file}")
        return 1

    print(f"\n📄 Analyzing enhanced extraction...")
    enhanced = analyze_bboxes(enhanced_file)

    print("\n" + "=" * 80)
    print("📈 RESULTS")
    print("=" * 80)

    print(f"\n✅ ENHANCED EXTRACTION:")
    print(f"   Total requirements: {enhanced['total']}")
    print(f"   With bounding boxes: {enhanced['with_bbox']} ({enhanced['with_bbox']/enhanced['total']*100:.1f}%)")

    # Analyze bbox dimensions
    heights = [s['height'] for s in enhanced['sizes']]
    widths = [s['width'] for s in enhanced['sizes']]

    if heights:
        avg_height = sum(heights) / len(heights)
        max_height = max(heights)
        min_height = min(heights)

        print(f"\n📏 Bounding Box Dimensions:")
        print(f"   Average height: {avg_height:.3f}")
        print(f"   Max height: {max_height:.3f}")
        print(f"   Min height: {min_height:.3f}")
        print(f"   Height > 0.05 (multi-line): {sum(1 for h in heights if h > 0.05)} / {len(heights)}")
        print(f"   Height > 0.08 (3+ lines): {sum(1 for h in heights if h > 0.08)} / {len(heights)}")

    # Show examples of large bboxes (likely multi-line)
    large_bboxes = sorted([s for s in enhanced['sizes'] if s['height'] > 0.06],
                          key=lambda x: x['height'], reverse=True)

    if large_bboxes:
        print(f"\n📦 Top 5 Largest Bounding Boxes (Multi-line Requirements):")
        print(f"   {'ID':<12} {'Height':<10} {'Width':<10} {'Text Len':<10}")
        print("   " + "-" * 50)
        for bbox in large_bboxes[:5]:
            print(f"   {bbox['id']:<12} {bbox['height']:<10.3f} {bbox['width']:<10.3f} {bbox['text_len']:<10}")

    print("\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
