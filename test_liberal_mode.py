#!/usr/bin/env python3
"""
Simple test script to verify the liberal mode service implementation.
"""

import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_liberal_mode_service_import():
    """Test that the liberal mode service can be imported."""
    try:
        from backend.services import LiberalModeService
        print("[PASS] LiberalModeService imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import LiberalModeService: {e}")
        return False

def test_liberal_mode_service_instantiation():
    """Test that the liberal mode service can be instantiated."""
    try:
        from backend.services import LiberalModeService
        service = LiberalModeService()
        print("[PASS] LiberalModeService instantiated successfully")
        print(f"  - Ollama URL: {service.ollama_url}")
        print(f"  - Model name: {service.model_name}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to instantiate LiberalModeService: {e}")
        return False

def test_liberal_mode_service_health_check():
    """Test that the liberal mode service health check runs (expected to fail without Ollama)."""
    try:
        from backend.services import LiberalModeService
        service = LiberalModeService()
        is_healthy = service.health_check()
        print(f"[PASS] LiberalModeService health check completed (healthy: {is_healthy})")
        # We expect this to be False since Ollama is likely not running
        return True
    except Exception as e:
        print(f"[FAIL] LiberalModeService health check failed with exception: {e}")
        return False

def test_format_context_method():
    """Test the _format_context method."""
    try:
        from backend.services import LiberalModeService
        service = LiberalModeService()

        # Test with empty results
        empty_result = service._format_context([])
        print(f"[PASS] Empty context formatting: '{empty_result}'")

        # Test with sample results
        sample_results = [
            {
                "text": "This is a sample chunk of text.",
                "metadata": {
                    "document_name": "sample.pdf",
                    "page_number": 1
                }
            },
            {
                "text": "This is another sample chunk.",
                "metadata": {
                    "document_name": "sample.pdf",
                    "page_number": 2
                }
            }
        ]
        formatted = service._format_context(sample_results)
        print("[PASS] Sample context formatting successful")
        print(f"  Formatted context length: {len(formatted)} characters")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to test _format_context method: {e}")
        return False

def test_create_liberal_prompt_method():
    """Test the _create_liberal_prompt method."""
    try:
        from backend.services import LiberalModeService
        service = LiberalModeService()

        context = "[Source 1: test.pdf, Page 1]\nThis is test context."
        question = "What is the test about?"
        prompt = service._create_liberal_prompt(question, context)

        print("[PASS] Liberal prompt creation successful")
        print(f"  Prompt length: {len(prompt)} characters")
        # Check that key components are present
        assert "DOCUMENT-BASED ANSWER:" in prompt
        assert "ADDITIONAL EXPLANATION:" in prompt
        assert context in prompt
        assert question in prompt
        print("  [PASS] Prompt contains required sections")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to test _create_liberal_prompt method: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Liberal Mode Service Implementation")
    print("=" * 50)

    tests = [
        test_liberal_mode_service_import,
        test_liberal_mode_service_instantiation,
        test_liberal_mode_service_health_check,
        test_format_context_method,
        test_create_liberal_prompt_method
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Add blank line between tests

    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())