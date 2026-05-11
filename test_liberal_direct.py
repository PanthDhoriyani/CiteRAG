#!/usr/bin/env python3
"""
Direct test of Liberal Mode service with mock data to verify the logic works.
"""

import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_liberal_mode_with_mock_data():
    """Test liberal mode service directly with mock search results."""
    try:
        from backend.services import LiberalModeService

        # Create service instance
        service = LiberalModeService()
        print("[PASS] LiberalModeService instantiated")

        # Mock search results (what we'd get from retriever + reranker)
        mock_search_results = [
            {
                "text": "The capital of France is Paris. It is located in the north-central part of the country.",
                "metadata": {
                    "document_name": "france_guide.pdf",
                    "page_number": 5,
                    "document_id": "doc123"
                }
            },
            {
                "text": "Paris is known for its art, culture, and historical landmarks like the Eiffel Tower and Louvre Museum.",
                "metadata": {
                    "document_name": "france_guide.pdf",
                    "page_number": 7,
                    "document_id": "doc123"
                }
            }
        ]

        # Test the generate_liberal_answer method directly
        # Note: This will fail if Ollama is not running, but we know it is from earlier tests
        question = "What is the capital of France and what is it known for?"

        print(f"[INFO] Testing with question: {question}")
        print(f"[INFO] Using {len(mock_search_results)} mock search results")

        # This will call Ollama - should work since we know Ollama is running
        response = service.generate_liberal_answer(question, mock_search_results)

        print("[PASS] Liberal mode answer generated successfully!")
        print(f"[INFO] Response keys: {list(response.keys())}")
        print(f"[INFO] Answer keys: {list(response['answer'].keys())}")
        print(f"[INFO] Metadata: {response['metadata']}")

        # Check the structure
        answer = response['answer']
        metadata = response['metadata']

        assert 'document_based' in answer
        assert 'additional_explanation' in answer
        assert 'citations' in answer
        assert metadata['mode'] == 'liberal'
        assert 'llm_model' in metadata
        assert 'processing_time_ms' in metadata

        print(f"[INFO] Document-based answer length: {len(answer['document_based'])} chars")
        print(f"[INFO] Additional explanation length: {len(answer['additional_explanation'])} chars")
        print(f"[INFO] Number of citations: {len(answer['citations'])}")

        # Show a preview
        print("\n" + "="*50)
        print("SAMPLE RESPONSE:")
        print("="*50)
        print(f"DOCUMENT-BASED ANSWER:\n{answer['document_based'][:200]}...")
        print(f"\nADDITIONAL EXPLANATION:\n{answer['additional_explanation'][:200]}...")
        print("="*50)

        return True

    except Exception as e:
        print(f"[FAIL] Liberal mode direct test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the direct test."""
    print("Testing Liberal Mode Service Directly")
    print("=" * 50)

    success = test_liberal_mode_with_mock_data()

    print("=" * 50)
    if success:
        print("✅ Direct liberal mode test PASSED")
        print("The liberal mode service implementation is working correctly!")
        return 0
    else:
        print("❌ Direct liberal mode test FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())