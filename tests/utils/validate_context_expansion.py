#!/usr/bin/env python3
"""
Context Expansion Validation Script
====================================

Analyzes the Document AI output to validate context expansion improvements.
Checks for:
- Truncated requirements (ending mid-sentence)
- Complete requirements
- Average requirement length
- Requirements that clearly benefited from expansion
"""

import json
import re
from pathlib import Path
from typing import Dict, List


def load_output(filepath: str) -> dict:
    """Load Document AI output JSON"""
    with open(filepath, 'r') as f:
        return json.load(f)


def is_truncated(text: str) -> bool:
    """
    Detect if requirement text is truncated mid-sentence

    Indicators of truncation:
    - Ends with "the", "and", "or", "with", "for", "to", "a", "an" (incomplete)
    - Missing ending punctuation
    - Very short (< 30 chars) without clear ending
    """
    text = text.strip()

    # Check if ends with common incomplete words
    truncation_words = [
        r'\bthe$', r'\band$', r'\bor$', r'\bwith$', r'\bfor$',
        r'\bto$', r'\ba$', r'\ban$', r'\bin$', r'\bof$', r'\bat$',
        r'\bfrom$', r'\bas$', r'\bthat$', r'\bthis$', r'\bwhich$'
    ]

    for pattern in truncation_words:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Check for missing ending punctuation (but not section headers)
    if not re.search(r'[.!?:]$', text):
        # Allow if it's clearly a title/header (all caps or Title Case and short)
        if len(text) < 50 and (text.isupper() or text.istitle()):
            return False
        return True

    return False


def is_complete_requirement(text: str) -> bool:
    """Check if requirement appears complete"""
    text = text.strip()

    # Has proper ending punctuation
    if re.search(r'[.!?]$', text):
        # Not too short
        if len(text) >= 30:
            # Doesn't end with incomplete word
            if not is_truncated(text):
                return True

    # Section headers with colons can be complete
    if re.search(r'[:]$', text) and len(text) >= 20:
        return True

    return False


def analyze_requirement(req: Dict) -> Dict:
    """Analyze a single requirement"""
    text = req.get('text', '')
    req_id = req.get('id', 'UNKNOWN')
    req_type = req.get('type', 'UNKNOWN')

    return {
        'id': req_id,
        'type': req_type,
        'text': text,
        'length': len(text),
        'is_truncated': is_truncated(text),
        'is_complete': is_complete_requirement(text),
        'ends_with': text.split()[-1] if text else ''
    }


def generate_report(data: dict) -> str:
    """Generate validation report"""

    all_requirements = []

    # Collect all requirements from chunks
    for chunk in data.get('chunks', []):
        for req in chunk.get('detected_requirements', []):
            analysis = analyze_requirement(req)
            analysis['chunk_id'] = chunk.get('chunk_id')
            analysis['page'] = chunk.get('page_number')
            all_requirements.append(analysis)

    # Calculate statistics
    total_reqs = len(all_requirements)
    truncated_reqs = [r for r in all_requirements if r['is_truncated']]
    complete_reqs = [r for r in all_requirements if r['is_complete']]

    avg_length = sum(r['length'] for r in all_requirements) / total_reqs if total_reqs > 0 else 0

    # Generate report
    report = []
    report.append("=" * 80)
    report.append("📊 CONTEXT EXPANSION VALIDATION REPORT")
    report.append("=" * 80)
    report.append("")

    report.append("📈 OVERALL STATISTICS")
    report.append(f"  Total requirements: {total_reqs}")
    report.append(f"  Complete requirements: {len(complete_reqs)} ({len(complete_reqs)/total_reqs*100:.1f}%)")
    report.append(f"  Truncated requirements: {len(truncated_reqs)} ({len(truncated_reqs)/total_reqs*100:.1f}%)")
    report.append(f"  Average length: {avg_length:.1f} characters")
    report.append("")

    # Length distribution
    short_reqs = [r for r in all_requirements if r['length'] < 50]
    medium_reqs = [r for r in all_requirements if 50 <= r['length'] < 150]
    long_reqs = [r for r in all_requirements if r['length'] >= 150]

    report.append("📏 LENGTH DISTRIBUTION")
    report.append(f"  Short (< 50 chars): {len(short_reqs)} ({len(short_reqs)/total_reqs*100:.1f}%)")
    report.append(f"  Medium (50-150 chars): {len(medium_reqs)} ({len(medium_reqs)/total_reqs*100:.1f}%)")
    report.append(f"  Long (≥ 150 chars): {len(long_reqs)} ({len(long_reqs)/total_reqs*100:.1f}%)")
    report.append("")

    # Show truncated requirements
    if truncated_reqs:
        report.append("❌ TRUNCATED REQUIREMENTS (Needs Improvement)")
        report.append("")
        for i, req in enumerate(truncated_reqs[:10], 1):  # Show first 10
            report.append(f"{i}. {req['id']} (Page {req['page']}) - {req['length']} chars")
            report.append(f"   Type: {req['type']}")
            report.append(f"   Text: \"{req['text']}\"")
            report.append(f"   Ends with: \"{req['ends_with']}\" ← Incomplete!")
            report.append("")

        if len(truncated_reqs) > 10:
            report.append(f"   ... and {len(truncated_reqs) - 10} more truncated requirements")
            report.append("")

    # Show complete requirements (sample)
    if complete_reqs:
        report.append("✅ COMPLETE REQUIREMENTS (Sample)")
        report.append("")
        # Show longest complete requirements (likely expanded successfully)
        complete_reqs_sorted = sorted(complete_reqs, key=lambda x: x['length'], reverse=True)
        for i, req in enumerate(complete_reqs_sorted[:5], 1):
            report.append(f"{i}. {req['id']} (Page {req['page']}) - {req['length']} chars")
            report.append(f"   Type: {req['type']}")
            report.append(f"   Text: \"{req['text']}\"")
            report.append("")

    # Success metrics
    report.append("=" * 80)
    report.append("🎯 SUCCESS METRICS")
    report.append("=" * 80)

    success_rate = (len(complete_reqs) / total_reqs * 100) if total_reqs > 0 else 0

    report.append(f"✅ Completeness Rate: {success_rate:.1f}%")

    if success_rate >= 80:
        report.append("   Status: ✅ EXCELLENT - Context expansion working well!")
    elif success_rate >= 60:
        report.append("   Status: ⚠️  GOOD - Some improvements possible")
    else:
        report.append("   Status: ❌ NEEDS IMPROVEMENT - Many truncated requirements")

    report.append("")
    report.append(f"📊 Average Length: {avg_length:.1f} chars")

    if avg_length >= 100:
        report.append("   Status: ✅ GOOD - Requirements have substantial content")
    elif avg_length >= 60:
        report.append("   Status: ⚠️  MODERATE - Could be more detailed")
    else:
        report.append("   Status: ❌ SHORT - Requirements may be incomplete")

    report.append("")
    report.append("=" * 80)
    report.append("✨ VALIDATION COMPLETE")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    """Main validation function"""

    # Load Document AI output
    project_root = Path(__file__).parent.parent.parent
    output_file = project_root / "tests" / "outputs" / "test_enhanced_bbox_output.json"

    try:
        data = load_output(str(output_file))
        report = generate_report(data)

        # Print report
        print(report)

        # Save report to file
        with open('context_expansion_validation_report.txt', 'w') as f:
            f.write(report)

        print("\n📄 Report saved to: context_expansion_validation_report.txt")

    except FileNotFoundError:
        print(f"❌ Error: {output_file} not found")
        print("   Run test_enhanced_bbox.py first to generate the output")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
