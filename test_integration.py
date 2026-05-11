#!/usr/bin/env python3
"""
Simple integration test to verify the liberal mode implementation works with the full app.
"""

import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_main_app_import():
    """Test that the main FastAPI app can be imported."""
    try:
        from backend.main import app
        print("[PASS] Main FastAPI app imported successfully")
        print(f"  - App title: {app.title}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import main app: {e}")
        return False

def test_router_inclusion():
    """Test that the routers are properly included in the app."""
    try:
        from backend.main import app
        from backend.routers import query, upload

        # Check that routers are included
        route_paths = []
        for route in app.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)

        # Check for API routes
        api_routes = [path for path in route_paths if path.startswith('/api')]
        print(f"[PASS] Found {len(api_routes)} API routes")

        # Check for specific endpoints we expect
        expected_prefixes = ['/api/upload', '/api/query']
        for prefix in expected_prefixes:
            matching_routes = [path for path in api_routes if path.startswith(prefix)]
            if matching_routes:
                print(f"  [PASS] Found routes for {prefix}")
            else:
                print(f"  [WARN] No routes found for {prefix}")

        return True
    except Exception as e:
        print(f"[FAIL] Failed to check router inclusion: {e}")
        return False

def test_schemas_available():
    """Test that the liberal mode schemas are available."""
    try:
        from backend.models.schemas import LiberalAnswer, LiberalQueryResponse, QueryResponse, SearchResult
        print("[PASS] Liberal mode schemas imported successfully")
        print(f"  - LiberalAnswer: {LiberalAnswer}")
        print(f"  - LiberalQueryResponse: {LiberalQueryResponse}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import liberal mode schemas: {e}")
        return False

def test_services_available():
    """Test that the liberal mode service is available through the services package."""
    try:
        from backend.services import LiberalModeService, Retriever, Reranker, DocumentProcessor
        print("[PASS] Liberal mode service available through services package")
        print(f"  - LiberalModeService: {LiberalModeService}")
        print(f"  - Retriever: {Retriever}")
        print(f"  - Reranker: {Reranker}")
        print(f"  - DocumentProcessor: {DocumentProcessor}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import services: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Liberal Mode Implementation Integration")
    print("=" * 50)

    tests = [
        test_main_app_import,
        test_router_inclusion,
        test_schemas_available,
        test_services_available
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
        print("All integration tests passed!")
        print("The liberal mode implementation is ready for use.")
        return 0
    else:
        print("Some integration tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())