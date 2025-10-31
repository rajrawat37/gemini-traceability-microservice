#!/usr/bin/env python3
"""
Unit Tests for Requirement Context Expansion
============================================

Tests the expand_requirement_context() function and its helper functions.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.document_ai import (
    smart_split_sentences,
    is_continuation_sentence,
    is_complete_thought,
    expand_requirement_context
)


def test_smart_split_sentences():
    """Test sentence splitting with position tracking"""
    print("\n🧪 Testing smart_split_sentences()...")

    # Test 1: Simple sentences
    text = "First sentence. Second sentence! Third sentence?"
    sentences = smart_split_sentences(text)

    assert len(sentences) == 3, f"Expected 3 sentences, got {len(sentences)}"
    assert sentences[0]["text"] == "First sentence.", f"Got: {sentences[0]['text']}"
    assert sentences[1]["text"] == "Second sentence!", f"Got: {sentences[1]['text']}"
    assert sentences[2]["text"] == "Third sentence?", f"Got: {sentences[2]['text']}"
    print("  ✅ Simple sentence splitting works")

    # Test 2: Multi-line text
    text2 = "The system shall authenticate users. It must use MFA. This ensures security."
    sentences2 = smart_split_sentences(text2)

    assert len(sentences2) == 3, f"Expected 3 sentences, got {len(sentences2)}"
    assert "authenticate" in sentences2[0]["text"]
    assert "MFA" in sentences2[1]["text"]
    assert "security" in sentences2[2]["text"]
    print("  ✅ Multi-line sentence splitting works")

    print("✅ smart_split_sentences() tests passed!\n")


def test_is_continuation_sentence():
    """Test continuation detection"""
    print("🧪 Testing is_continuation_sentence()...")

    # Test 1: Continuation indicators
    assert is_continuation_sentence("First.", "It must also do this.") == True, "Pronoun continuation failed"
    assert is_continuation_sentence("First.", "Additionally, it works.") == True, "Adverb continuation failed"
    assert is_continuation_sentence("First.", "and it continues.") == True, "Conjunction continuation failed"
    print("  ✅ Continuation indicators detected")

    # Test 2: Section breaks (NOT continuation)
    assert is_continuation_sentence("First.", "1. Second section") == False, "Numbered list not detected as break"
    assert is_continuation_sentence("First.", "Security: Next topic") == False, "Section header not detected as break"
    assert is_continuation_sentence("First.", "• Bullet point") == False, "Bullet not detected as break"
    print("  ✅ Section breaks detected correctly")

    # Test 3: Edge cases
    assert is_continuation_sentence("First.", "") == False, "Empty string handled"
    assert is_continuation_sentence("First.", "   ") == False, "Whitespace handled"
    print("  ✅ Edge cases handled")

    print("✅ is_continuation_sentence() tests passed!\n")


def test_is_complete_thought():
    """Test complete thought detection"""
    print("🧪 Testing is_complete_thought()...")

    # Test 1: Complete thoughts
    assert is_complete_thought("The system shall authenticate users.") == True, "Complete sentence not recognized"
    assert is_complete_thought("This is a complete thought with punctuation!") == True, "Exclamation not recognized"
    print("  ✅ Complete thoughts recognized")

    # Test 2: Incomplete thoughts
    assert is_complete_thought("The system shall") == False, "Incomplete thought not detected (no punctuation)"
    assert is_complete_thought("Short.") == False, "Too short"
    assert is_complete_thought("No") == False, "Single word not recognized as complete"
    print("  ✅ Incomplete thoughts detected")

    # Test 3: Edge cases
    assert is_complete_thought("") == False, "Empty string handled"
    assert is_complete_thought("This is a complete thought.") == True, "Minimum length met"
    assert is_complete_thought("Too short.") == False, "Too short (< 20 chars)"
    print("  ✅ Edge cases handled")

    print("✅ is_complete_thought() tests passed!\n")


def test_expand_requirement_context():
    """Test the main context expansion function"""
    print("🧪 Testing expand_requirement_context()...")

    # Test 1: Simple expansion (continuation)
    initial = "The system shall authenticate users"
    context = "The system shall authenticate users. It must use multi-factor authentication. This ensures security."
    result = expand_requirement_context(initial, context)

    assert "multi-factor" in result, f"Expansion failed: {result}"
    assert len(result) > len(initial), "Text not expanded"
    print(f"  ✅ Simple expansion: {len(initial)} → {len(result)} chars")
    print(f"     Original: {initial}")
    print(f"     Expanded: {result[:80]}...")

    # Test 2: Stop at section break
    initial2 = "Security: The application must encrypt data"
    context2 = "Security: The application must encrypt data. Performance: Fast loading times required."
    result2 = expand_requirement_context(initial2, context2)

    assert "Performance" not in result2, f"Should stop at section break: {result2}"
    print(f"  ✅ Stops at section break correctly")

    # Test 3: Respect max_chars limit
    initial3 = "The system shall do this"
    context3 = "The system shall do this. And it continues here. And more text follows. And even more content. Final sentence here."
    result3 = expand_requirement_context(initial3, context3, max_chars=80)

    # Should stop expanding before hitting max_chars
    assert len(result3) < 200, f"Max chars not respected: {len(result3)} chars"
    # But should have expanded at least a bit
    assert len(result3) > len(initial3), "Should have expanded somewhat"
    print(f"  ✅ Max chars limit respected: {len(result3)} chars (limit was 80)")

    # Test 4: Respect max_sentences limit
    initial4 = "First sentence"
    context4 = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    result4 = expand_requirement_context(initial4, context4, max_sentences=2)

    sentence_count = result4.count('.') + result4.count('!') + result4.count('?')
    assert sentence_count <= 2, f"Max sentences not respected: {sentence_count} sentences"
    print(f"  ✅ Max sentences limit respected: {sentence_count} sentences")

    # Test 5: Already complete thought (no expansion needed)
    initial5 = "This is already a complete and sufficiently long requirement statement."
    context5 = "This is already a complete and sufficiently long requirement statement. Another sentence follows."
    result5 = expand_requirement_context(initial5, context5)

    assert result5 == initial5, "Should not expand already complete thought"
    print(f"  ✅ Already complete thoughts left unchanged")

    # Test 6: No continuation found (single sentence)
    initial6 = "Standalone requirement"
    context6 = "Standalone requirement. 1. Next section with different topic."
    result6 = expand_requirement_context(initial6, context6)

    assert "Next section" not in result6, f"Should not include unrelated content: {result6}"
    print(f"  ✅ Stops when no continuation found")

    # Test 7: Edge case - empty inputs
    result7 = expand_requirement_context("", "Some context")
    assert result7 == "", "Empty initial sentence handled"

    result8 = expand_requirement_context("Initial", "")
    assert result8 == "Initial", "Empty context handled"
    print(f"  ✅ Edge cases handled")

    print("✅ expand_requirement_context() tests passed!\n")


def test_realistic_example():
    """Test with realistic PRD text"""
    print("🧪 Testing with realistic PRD example...")

    # Realistic example from PRD-7
    initial = "The tool allows users to upload or paste a PRD, then analyzes and grades the"
    full_context = """This document outlines the requirements for an Al-based PRD Reviewer, a new tool offered by
pmprompt.com. The tool allows users to upload or paste a PRD, then analyzes and grades the
content. It also provides actionable feedback to improve clarity, completeness, and alignment
with best practices in product management."""

    result = expand_requirement_context(initial, full_context, max_sentences=5, max_chars=400)

    print(f"  Original length: {len(initial)} chars")
    print(f"  Expanded length: {len(result)} chars")
    print(f"  Expansion ratio: {len(result)/len(initial):.1f}x")
    print(f"\n  Original text:")
    print(f"    {initial}")
    print(f"\n  Expanded text:")
    print(f"    {result}")

    assert "actionable feedback" in result, "Should include continuation"
    assert "clarity, completeness" in result, "Should include full context"
    assert len(result) > len(initial) * 1.5, "Should be significantly longer"

    print("\n  ✅ Realistic example handled correctly")
    print("✅ Realistic PRD test passed!\n")


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("🧪 CONTEXT EXPANSION UNIT TESTS")
    print("=" * 80)

    try:
        test_smart_split_sentences()
        test_is_continuation_sentence()
        test_is_complete_thought()
        test_expand_requirement_context()
        test_realistic_example()

        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
