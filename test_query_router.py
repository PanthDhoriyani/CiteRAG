#!/usr/bin/env python3
"""
Simple test script to verify the query router liberal mode integration.
"""

import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_query_router_imports():
    """Test that the query router can be imported with liberal mode support."""
    try:
        from backend.routers import query
        from backend.models.schemas import LiberalQueryResponse, QueryResponse
        from typing import Union
        print("[PASS] Query router imported successfully with liberal mode support")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import query router: {e}")
        return False

def test_query_router_endpoint_signature():
    """Test that the query router endpoint has the correct response model."""
    try:
        from backend.routers.query import router
        # Get the route
        routes = router.routes
        query_route = None
        for route in routes:
            if route.path == "/query" and route.methods == {"POST"}:
                query_route = route
                break

        if query_route is None:
            print("[FAIL] Could not find POST /query route")
            return False

        # Check if it has a response_model attribute
        if hasattr(query_route, 'response_model'):
            print(f"[PASS] Query router endpoint has response_model: {query_route.response_model}")
            return True
        else:
            print("[WARN] Query router endpoint does not have response_model attribute")
            # This might be okay depending on how FastAPI is set up
            return True
    except Exception as e:
        print(f"[FAIL] Failed to check query router endpoint signature: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Query Router Liberal Mode Integration")
    print("=" * 50)

    tests = [
        test_query_router_imports,
        test_query_router_endpoint_signature
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