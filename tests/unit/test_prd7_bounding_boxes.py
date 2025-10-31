#!/usr/bin/env python3
"""
PRD-7 Bounding Box Verification Test
=====================================

This script tests and verifies that the complete pipeline (Document AI → DLP → RAG → KG → Test Generation)
correctly extracts, preserves, and delivers requirement-specific bounding boxes for PRD-7.pdf.

Verification includes:
1. Requirement text is complete and meaningful (not fragments)
2. Bounding boxes point to correct locations in PDF
3. Text at bounding box coordinates matches the requirement text
4. All pipeline stages preserve bounding box data correctly
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
from difflib import SequenceMatcher

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import pipeline modules
from modules.document_ai import extract_traceable_docai
from modules.dlp_masking import mask_chunks_with_dlp
from modules.rag_enhancement import query_rag_from_chunks
from modules.knowledge_graph import build_knowledge_graph_from_rag
from modules.test_generation import generate_test_cases_with_rag_context, enrich_test_cases_for_ui

# Try to import PDF libraries
try:
    import fitz  # PyMuPDF
    PDF_LIBRARY = "pymupdf"
except ImportError:
    try:
        import pdfplumber
        PDF_LIBRARY = "pdfplumber"
    except ImportError:
        print("⚠️  Warning: No PDF library available. Install PyMuPDF (pip install pymupdf) or pdfplumber")
        PDF_LIBRARY = None


class BoundingBoxVerifier:
    """Verifies bounding box accuracy and requirement text quality"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_doc = None
        self.results = {
            "total_requirements": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": []
        }

        # Load PDF
        if PDF_LIBRARY == "pymupdf":
            self.pdf_doc = fitz.open(pdf_path)
        elif PDF_LIBRARY == "pdfplumber":
            self.pdf_doc = pdfplumber.open(pdf_path)

    def validate_requirement_text_quality(self, req_text: str, req_type: str) -> Dict[str, Any]:
        """
        Validates that requirement text is complete and meaningful

        Returns:
            Dict with quality metrics and pass/fail status
        """
        issues = []
        warnings = []

        # Length check
        text_length = len(req_text.strip())
        if text_length < 20:
            issues.append(f"Too short ({text_length} chars) - likely incomplete")

        # Completeness checks
        stripped_text = req_text.strip()

        # Check proper capitalization at start
        if stripped_text and not stripped_text[0].isupper():
            warnings.append("Does not start with capital letter")

        # Check proper ending (punctuation or complete phrase)
        if stripped_text and not re.search(r'[.!?;:]$', stripped_text):
            if len(stripped_text) > 50:  # Long text should have punctuation
                issues.append("Missing ending punctuation - possibly incomplete")
            else:
                warnings.append("No ending punctuation")

        # Check for modal verbs if it's a MODAL_VERB type
        modal_verbs = r'\b(shall|must|should|will|may|can)\b'
        has_modal_verb = bool(re.search(modal_verbs, req_text, re.IGNORECASE))

        if req_type == "MODAL_VERB" and not has_modal_verb:
            issues.append(f"Type is {req_type} but no modal verb found")

        # Check for meaningful content (has subject-verb structure)
        # Simple heuristic: should have multiple words and some common verbs/nouns
        words = req_text.split()
        if len(words) < 4:
            issues.append(f"Too few words ({len(words)}) - likely a fragment")

        # Check for incomplete fragments (common patterns)
        fragment_patterns = [
            r'^(The|A|An)\s+\w+$',  # Just "The system" or "A user"
            r'^\w+\s+(can|will|shall|must|should)$',  # Just "Users can"
            r'^(encrypt|verify|validate|check|ensure)\b',  # Starts with verb only
        ]

        for pattern in fragment_patterns:
            if re.match(pattern, stripped_text, re.IGNORECASE):
                issues.append(f"Appears to be incomplete fragment: '{stripped_text}'")
                break

        # Calculate quality score (0-100)
        quality_score = 100
        quality_score -= len(issues) * 20
        quality_score -= len(warnings) * 5
        quality_score = max(0, quality_score)

        return {
            "text": req_text,
            "length": text_length,
            "has_modal_verb": has_modal_verb,
            "quality_score": quality_score,
            "is_complete": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "status": "PASS" if len(issues) == 0 else "FAIL"
        }

    def validate_bounding_box_coords(self, bbox: Dict) -> Dict[str, Any]:
        """Validates bounding box coordinate structure and values"""
        issues = []

        # Check all required fields exist
        required_fields = ["x_min", "y_min", "x_max", "y_max"]
        for field in required_fields:
            if field not in bbox:
                issues.append(f"Missing field: {field}")

        if issues:
            return {"valid": False, "issues": issues}

        # Check value ranges (normalized coordinates should be 0.0-1.0)
        for field in required_fields:
            value = bbox[field]
            if not isinstance(value, (int, float)):
                issues.append(f"{field} is not a number: {value}")
            elif value < 0 or value > 1:
                issues.append(f"{field} out of range [0,1]: {value}")

        # Check logical consistency
        if "x_min" in bbox and "x_max" in bbox:
            if bbox["x_max"] <= bbox["x_min"]:
                issues.append(f"x_max ({bbox['x_max']}) must be > x_min ({bbox['x_min']})")

        if "y_min" in bbox and "y_max" in bbox:
            if bbox["y_max"] <= bbox["y_min"]:
                issues.append(f"y_max ({bbox['y_max']}) must be > y_min ({bbox['y_min']})")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "bbox": bbox
        }

    def extract_text_at_bbox(self, page_num: int, bbox: Dict) -> str:
        """Extract text from PDF at specific bounding box coordinates"""
        if not self.pdf_doc or not PDF_LIBRARY:
            return "[PDF extraction not available]"

        try:
            # Page numbers are 1-indexed in our system, but 0-indexed in libraries
            page_idx = page_num - 1

            if PDF_LIBRARY == "pymupdf":
                if page_idx >= len(self.pdf_doc):
                    return f"[Page {page_num} out of range]"

                page = self.pdf_doc[page_idx]
                page_rect = page.rect

                # Convert normalized coordinates to actual coordinates
                x0 = bbox["x_min"] * page_rect.width
                y0 = bbox["y_min"] * page_rect.height
                x1 = bbox["x_max"] * page_rect.width
                y1 = bbox["y_max"] * page_rect.height

                # Extract text from rectangle
                rect = fitz.Rect(x0, y0, x1, y1)
                text = page.get_text("text", clip=rect)
                return text.strip()

            elif PDF_LIBRARY == "pdfplumber":
                if page_idx >= len(self.pdf_doc.pages):
                    return f"[Page {page_num} out of range]"

                page = self.pdf_doc.pages[page_idx]

                # Convert normalized coordinates to actual coordinates
                x0 = bbox["x_min"] * page.width
                y0 = bbox["y_min"] * page.height
                x1 = bbox["x_max"] * page.width
                y1 = bbox["y_max"] * page.height

                # Crop page to bounding box and extract text
                cropped = page.within_bbox((x0, y0, x1, y1))
                text = cropped.extract_text()
                return text.strip() if text else ""

        except Exception as e:
            return f"[Error extracting text: {str(e)}]"

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two texts (0.0 - 1.0)"""
        # Normalize texts for comparison
        norm1 = ' '.join(text1.lower().split())
        norm2 = ' '.join(text2.lower().split())

        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity

    def verify_requirement(self, test_case: Dict, test_id: str) -> Dict:
        """
        Comprehensive verification of a single requirement's bounding box and text quality
        """
        result = {
            "test_id": test_id,
            "requirement_id": test_case.get("derived_from", "UNKNOWN"),
            "status": "PASS",
            "checks": {}
        }

        # Get traceability data
        traceability = test_case.get("traceability", {})
        req_text = traceability.get("requirement_text", "")
        req_type = "MODAL_VERB"  # Default assumption

        # Check 1: Validate requirement text quality
        quality_check = self.validate_requirement_text_quality(req_text, req_type)
        result["checks"]["text_quality"] = quality_check

        if quality_check["status"] == "FAIL":
            result["status"] = "FAIL"

        # Check 2: Validate bounding box exists and has correct structure
        pdf_locations = traceability.get("pdf_locations", [])

        if not pdf_locations:
            result["checks"]["bbox_exists"] = {
                "status": "FAIL",
                "issue": "No pdf_locations found"
            }
            result["status"] = "FAIL"
            return result

        location = pdf_locations[0]
        page_num = location.get("page_number", 0)
        bbox = location.get("bounding_box", {})

        result["page_number"] = page_num
        result["bounding_box"] = bbox

        # Check 3: Validate bounding box coordinates
        bbox_validation = self.validate_bounding_box_coords(bbox)
        result["checks"]["bbox_coords"] = bbox_validation

        if not bbox_validation["valid"]:
            result["status"] = "FAIL"
            return result

        # Check 4: Extract text from PDF at bounding box location
        extracted_text = self.extract_text_at_bbox(page_num, bbox)
        result["extracted_text"] = extracted_text
        result["expected_text"] = req_text

        # Check 5: Compare extracted text with requirement text
        if extracted_text and not extracted_text.startswith("["):
            similarity = self.calculate_text_similarity(req_text, extracted_text)
            result["checks"]["text_match"] = {
                "similarity": similarity,
                "threshold": 0.8,
                "status": "PASS" if similarity >= 0.8 else "FAIL"
            }

            if similarity < 0.8:
                result["status"] = "FAIL"
                result["checks"]["text_match"]["issue"] = f"Low similarity ({similarity:.2%})"

            # Check if extracted text is also complete
            extracted_quality = self.validate_requirement_text_quality(extracted_text, req_type)
            if not extracted_quality["is_complete"]:
                result["status"] = "WARNING"
                result["checks"]["extracted_quality"] = {
                    "status": "WARNING",
                    "issues": extracted_quality["issues"]
                }
        else:
            result["checks"]["text_match"] = {
                "status": "FAIL",
                "issue": f"Could not extract text: {extracted_text}"
            }
            result["status"] = "FAIL"

        return result

    def verify_all(self, test_categories: List[Dict]) -> Dict:
        """Verify all test cases and generate report"""
        print("🔍 Starting comprehensive bounding box verification...")
        print("=" * 80)

        all_results = []

        for category in test_categories:
            category_name = category.get("category_name", "Unknown")
            test_cases = category.get("test_cases", [])

            print(f"\n📂 Category: {category_name}")
            print(f"   Test cases: {len(test_cases)}")

            for test_case in test_cases:
                test_id = test_case.get("test_id", "UNKNOWN")
                result = self.verify_requirement(test_case, test_id)
                all_results.append(result)

                # Print quick status
                status_icon = "✅" if result["status"] == "PASS" else ("⚠️" if result["status"] == "WARNING" else "❌")
                print(f"   {status_icon} {test_id}: {result['requirement_id']}")

        # Calculate summary statistics
        total = len(all_results)
        passed = sum(1 for r in all_results if r["status"] == "PASS")
        warnings = sum(1 for r in all_results if r["status"] == "WARNING")
        failed = sum(1 for r in all_results if r["status"] == "FAIL")

        self.results = {
            "total_requirements": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "details": all_results
        }

        return self.results

    def generate_report(self) -> str:
        """Generate comprehensive verification report"""
        report_lines = []

        report_lines.append("\n" + "=" * 80)
        report_lines.append("📊 PRD-7 BOUNDING BOX VERIFICATION REPORT")
        report_lines.append("=" * 80)

        # Summary
        report_lines.append("\n## SUMMARY")
        report_lines.append(f"Total Requirements: {self.results['total_requirements']}")
        report_lines.append(f"✅ Passed: {self.results['passed']}")
        report_lines.append(f"⚠️  Warnings: {self.results['warnings']}")
        report_lines.append(f"❌ Failed: {self.results['failed']}")
        report_lines.append(f"Pass Rate: {self.results['pass_rate']:.1f}%")

        # Section 1: Requirement Text Quality Analysis
        report_lines.append("\n" + "=" * 80)
        report_lines.append("## SECTION 1: REQUIREMENT TEXT QUALITY ANALYSIS")
        report_lines.append("=" * 80)
        report_lines.append(f"{'Req ID':<15} {'Length':<8} {'Complete?':<12} {'Modal?':<8} {'Quality':<10} {'Status':<10}")
        report_lines.append("-" * 80)

        for detail in self.results["details"]:
            req_id = detail["requirement_id"]
            quality = detail["checks"].get("text_quality", {})

            report_lines.append(
                f"{req_id:<15} "
                f"{quality.get('length', 0):<8} "
                f"{'Yes' if quality.get('is_complete', False) else 'No':<12} "
                f"{'Yes' if quality.get('has_modal_verb', False) else 'No':<8} "
                f"{quality.get('quality_score', 0):<10} "
                f"{quality.get('status', 'UNKNOWN'):<10}"
            )

            # Show issues if any
            if quality.get('issues'):
                for issue in quality['issues']:
                    report_lines.append(f"  ⚠️  {issue}")

        # Section 2: Bounding Box Location Accuracy
        report_lines.append("\n" + "=" * 80)
        report_lines.append("## SECTION 2: BOUNDING BOX LOCATION ACCURACY")
        report_lines.append("=" * 80)
        report_lines.append(f"{'Req ID':<15} {'Page':<6} {'Bbox Valid?':<12} {'Text Match':<12} {'Similarity':<12} {'Status':<10}")
        report_lines.append("-" * 80)

        for detail in self.results["details"]:
            req_id = detail["requirement_id"]
            page = detail.get("page_number", "N/A")
            bbox_valid = detail["checks"].get("bbox_coords", {}).get("valid", False)
            text_match = detail["checks"].get("text_match", {})
            similarity = text_match.get("similarity", 0)

            report_lines.append(
                f"{req_id:<15} "
                f"{page:<6} "
                f"{'Yes' if bbox_valid else 'No':<12} "
                f"{text_match.get('status', 'N/A'):<12} "
                f"{f'{similarity:.1%}' if similarity else 'N/A':<12} "
                f"{detail['status']:<10}"
            )

        # Section 3: Detailed Issues
        report_lines.append("\n" + "=" * 80)
        report_lines.append("## SECTION 3: DETAILED ISSUES & FAILURES")
        report_lines.append("=" * 80)

        failures = [d for d in self.results["details"] if d["status"] == "FAIL"]
        warnings_list = [d for d in self.results["details"] if d["status"] == "WARNING"]

        if failures:
            report_lines.append("\n### FAILURES:")
            for detail in failures:
                report_lines.append(f"\n❌ {detail['test_id']} - {detail['requirement_id']}")
                report_lines.append(f"   Expected: {detail.get('expected_text', 'N/A')[:80]}...")
                report_lines.append(f"   Extracted: {detail.get('extracted_text', 'N/A')[:80]}...")

                # List all issues
                for check_name, check_data in detail["checks"].items():
                    if isinstance(check_data, dict):
                        if check_data.get("status") == "FAIL":
                            report_lines.append(f"   Issue in {check_name}: {check_data.get('issue', 'Unknown')}")
                        if check_data.get("issues"):
                            for issue in check_data["issues"]:
                                report_lines.append(f"   - {issue}")
        else:
            report_lines.append("\n✅ No failures!")

        if warnings_list:
            report_lines.append("\n### WARNINGS:")
            for detail in warnings_list:
                report_lines.append(f"\n⚠️  {detail['test_id']} - {detail['requirement_id']}")
                for check_name, check_data in detail["checks"].items():
                    if isinstance(check_data, dict) and check_data.get("warnings"):
                        for warning in check_data["warnings"]:
                            report_lines.append(f"   - {warning}")

        # Section 4: Success Summary
        report_lines.append("\n" + "=" * 80)
        report_lines.append("## SECTION 4: SUCCESSFUL VERIFICATIONS")
        report_lines.append("=" * 80)

        successes = [d for d in self.results["details"] if d["status"] == "PASS"]
        if successes:
            report_lines.append(f"\n✅ {len(successes)} requirements fully verified:")
            for detail in successes:
                report_lines.append(f"   ✓ {detail['requirement_id']} (Page {detail.get('page_number', 'N/A')})")

        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80 + "\n")

        return "\n".join(report_lines)

    def close(self):
        """Close PDF document"""
        if self.pdf_doc:
            if PDF_LIBRARY == "pymupdf":
                self.pdf_doc.close()
            elif PDF_LIBRARY == "pdfplumber":
                self.pdf_doc.close()


async def run_complete_pipeline(pdf_path: str) -> Dict:
    """Run the complete pipeline and return final JSON output"""
    print("\n🚀 Running Complete Pipeline...")
    print("=" * 80)

    # Read PDF
    with open(pdf_path, 'rb') as f:
        content = f.read()

    # Get environment variables
    project_id = os.getenv("PROJECT_ID", "poc-genai-hacks")
    location = os.getenv("LOCATION", "us")
    processor_id = os.getenv("PROCESSOR_ID", "e7f52140009fdda2")
    rag_corpus_name = os.getenv("RAG_CORPUS_NAME", "projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856")
    rag_location = os.getenv("RAG_LOCATION", "europe-west3")
    gemini_location = os.getenv("GEMINI_LOCATION", "us-central1")

    # Step 1: Document AI
    print("\n📄 Step 1: Document AI extraction...")
    docai_result = extract_traceable_docai(content, project_id, location, processor_id, "PRD-7.pdf")

    # Step 2: DLP
    print("🔒 Step 2: DLP masking...")
    dlp_result = await mask_chunks_with_dlp(docai_result, project_id, gdpr_mode=True)

    # Step 3: RAG
    print("🔍 Step 3: RAG enhancement...")
    rag_result = await query_rag_from_chunks(dlp_result, project_id, rag_corpus_name, rag_location)

    # Step 4: Knowledge Graph
    print("🕸️  Step 4: Knowledge Graph construction...")
    kg_result = build_knowledge_graph_from_rag(rag_result)

    # Step 5: Test Generation
    print("🧪 Step 5: Test case generation...")
    test_result = generate_test_cases_with_rag_context(rag_result, project_id, gemini_location, kg_result)

    # Step 6: UI Enrichment
    print("🎨 Step 6: UI enrichment...")
    ui_result = enrich_test_cases_for_ui(
        test_result.get("test_cases", []),
        kg_result,
        rag_result,
        dlp_result
    )

    return ui_result


async def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 PRD-7 BOUNDING BOX VERIFICATION TEST")
    print("=" * 80)

    # Check for PRD-7.pdf
    pdf_path = project_root / "mockData" / "documents" / "PRD-7.pdf"

    if not pdf_path.exists():
        print(f"❌ ERROR: PRD-7.pdf not found at {pdf_path}")
        return 1

    print(f"📄 PDF Path: {pdf_path}")
    print(f"📚 PDF Library: {PDF_LIBRARY or 'Not available'}")

    # Run pipeline
    try:
        ui_result = await run_complete_pipeline(str(pdf_path))

        # Save JSON output
        output_file = project_root / "tests" / "outputs" / "test_output_prd7.json"
        with open(output_file, 'w') as f:
            json.dump(ui_result, f, indent=2)
        print(f"\n💾 JSON output saved to: {output_file}")

        # Verify bounding boxes
        print("\n" + "=" * 80)
        print("🔍 VERIFICATION PHASE")
        print("=" * 80)

        verifier = BoundingBoxVerifier(str(pdf_path))
        test_categories = ui_result.get("test_categories", [])

        results = verifier.verify_all(test_categories)
        report = verifier.generate_report()

        # Print report
        print(report)

        # Save report
        report_file = project_root / "verification_report_prd7.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"📄 Verification report saved to: {report_file}")

        verifier.close()

        # Return exit code based on results
        if results["failed"] > 0:
            print(f"\n❌ TEST FAILED: {results['failed']} requirements failed verification")
            return 1
        elif results["warnings"] > 0:
            print(f"\n⚠️  TEST PASSED WITH WARNINGS: {results['warnings']} requirements have warnings")
            return 0
        else:
            print(f"\n✅ TEST PASSED: All {results['passed']} requirements verified successfully!")
            return 0

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
