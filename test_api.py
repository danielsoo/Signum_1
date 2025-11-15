#!/usr/bin/env python3
"""
SIGNUM API Test Script
Test the API endpoints to ensure everything is working
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"


def test_endpoint(endpoint: str, description: str, params: Dict[str, Any] = None) -> bool:
    """Test a single API endpoint"""
    print(f"\n🧪 Testing: {description}")
    print(f"📍 Endpoint: {endpoint}")

    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, params=params, timeout=10)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("success", True):
                print("✅ SUCCESS")

                # Print some sample data
                if "data" in data and data["data"]:
                    print("📋 Sample response:")
                    sample_data = json.dumps(data, indent=2)[:500]
                    print(f"{sample_data}...")
                elif "status" in data:
                    print(f"📋 Status: {data['status']}")

                return True
            else:
                print(f"❌ FAILED: Response indicates failure")
                print(f"📋 Response: {response.text[:200]}...")
                return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"📋 Response: {response.text[:200]}...")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Could not connect to API server")
        print("💡 Make sure the API server is running on port 8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timeout")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all API tests"""
    print("🏥 SIGNUM API Test Suite")
    print("=" * 50)

    # Check if server is running
    print("\n🔍 Checking if API server is running...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print("✅ API server is running!")
    except:
        print("❌ API server is not running!")
        print("💡 Start the server with: ./start_api.sh")
        sys.exit(1)

    # Test cases
    tests = [
        {
            "endpoint": "/health",
            "description": "Basic health check",
            "params": None
        },
        {
            "endpoint": "/api/v1/system/status",
            "description": "System status",
            "params": None
        },
        {
            "endpoint": "/api/v1/providers/search",
            "description": "Provider search by specialty",
            "params": {"specialty": "Cardiology", "limit": 3}
        },
        {
            "endpoint": "/api/v1/providers/search",
            "description": "Provider search by state",
            "params": {"state": "PA", "limit": 2}
        },
        {
            "endpoint": "/api/v1/providers/search",
            "description": "Provider search by name",
            "params": {"last_name": "Smith", "limit": 2}
        },
        {
            "endpoint": "/api/v1/hospitals/search",
            "description": "Hospital search by name",
            "params": {"name": "General", "limit": 3}
        },
        {
            "endpoint": "/api/v1/hospitals/enhanced-search",
            "description": "Enhanced hospital search",
            "params": {"query": "Medical Center", "limit": 2}
        }
    ]

    # Run tests
    passed = 0
    total = len(tests)

    for test in tests:
        success = test_endpoint(
            test["endpoint"],
            test["description"],
            test.get("params")
        )
        if success:
            passed += 1

        # Small delay between tests
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! API is working correctly.")
        print("📊 You can now access the interactive docs at:")
        print(f"   {BASE_URL}/docs")
    else:
        print(f"\n⚠️  Some tests failed. Check the API server logs.")

    # Example usage
    print("\n💡 Example API calls:")
    print(f"curl {BASE_URL}/health")
    print(
        f'curl "{BASE_URL}/api/v1/providers/search?specialty=Cardiology&limit=3"')
    print(f'curl "{BASE_URL}/api/v1/hospitals/search?name=General&limit=3"')


if __name__ == "__main__":
    main()
