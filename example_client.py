#!/usr/bin/env python3
"""
SIGNUM API Example Client
Demonstrates how to use the SIGNUM Healthcare Provider Intelligence API
"""

import requests
import json
from typing import List, Dict, Any, Optional


class SignumAPIClient:
    """Python client for SIGNUM Healthcare Provider Intelligence API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client"""
        self.base_url = base_url.rstrip('/')

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        return self._make_request("/health")

    def search_providers(self,
                         first_name: Optional[str] = None,
                         last_name: Optional[str] = None,
                         organization_name: Optional[str] = None,
                         specialty: Optional[str] = None,
                         city: Optional[str] = None,
                         state: Optional[str] = None,
                         postal_code: Optional[str] = None,
                         limit: int = 10) -> Dict[str, Any]:
        """Search healthcare providers"""
        params = {}
        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name
        if organization_name:
            params["organization_name"] = organization_name
        if specialty:
            params["specialty"] = specialty
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if postal_code:
            params["postal_code"] = postal_code
        params["limit"] = limit

        return self._make_request("/api/v1/providers/search", params)

    def get_provider_by_npi(self, npi: str) -> Dict[str, Any]:
        """Get provider details by NPI number"""
        return self._make_request(f"/api/v1/providers/{npi}")

    def search_hospitals(self,
                         name: Optional[str] = None,
                         city: Optional[str] = None,
                         state: Optional[str] = None,
                         ccn: Optional[str] = None,
                         include_predictions: bool = True,
                         include_risk_analysis: bool = True,
                         limit: int = 10) -> Dict[str, Any]:
        """Search hospitals"""
        params = {}
        if name:
            params["name"] = name
        if city:
            params["city"] = city
        if state:
            params["state"] = state
        if ccn:
            params["ccn"] = ccn
        params["include_predictions"] = include_predictions
        params["include_risk_analysis"] = include_risk_analysis
        params["limit"] = limit

        return self._make_request("/api/v1/hospitals/search", params)

    def get_hospital_comprehensive(self, ccn: str) -> Dict[str, Any]:
        """Get comprehensive hospital data"""
        return self._make_request(f"/api/v1/hospitals/{ccn}/comprehensive")

    def get_hospital_risk_analysis(self, ccn: str) -> Dict[str, Any]:
        """Get hospital risk analysis"""
        return self._make_request(f"/api/v1/hospitals/{ccn}/risk-analysis")

    def enhanced_hospital_search(self,
                                 query: str,
                                 include_google_data: bool = True,
                                 limit: int = 5) -> Dict[str, Any]:
        """Enhanced hospital search with Google Places integration"""
        params = {
            "query": query,
            "include_google_data": include_google_data,
            "limit": limit
        }
        return self._make_request("/api/v1/hospitals/enhanced-search", params)


def demo_provider_search():
    """Demonstrate provider search functionality"""
    print("\n🔍 PROVIDER SEARCH DEMO")
    print("-" * 40)

    client = SignumAPIClient()

    # Search by specialty
    print("Searching for cardiologists in Pennsylvania...")
    result = client.search_providers(
        specialty="Cardiology", state="PA", limit=3)

    if result.get("success"):
        providers = result["data"]["providers"]
        print(f"Found {len(providers)} providers:")

        for i, provider in enumerate(providers[:3], 1):
            print(f"\n{i}. {provider.get('name', 'N/A')}")
            print(f"   NPI: {provider.get('npi', 'N/A')}")
            if provider.get("taxonomies"):
                specialty = provider["taxonomies"][0].get("desc", "N/A")
                print(f"   Specialty: {specialty}")
            if provider.get("practice_addresses"):
                addr = provider["practice_addresses"][0]
                city = addr.get("city", "N/A")
                state = addr.get("state", "N/A")
                print(f"   Location: {city}, {state}")
    else:
        print(f"Search failed: {result.get('error', 'Unknown error')}")


def demo_hospital_search():
    """Demonstrate hospital search functionality"""
    print("\n🏥 HOSPITAL SEARCH DEMO")
    print("-" * 40)

    client = SignumAPIClient()

    # Search hospitals by name
    print("Searching for hospitals with 'General' in the name...")
    result = client.search_hospitals(name="General", limit=3)

    if result.get("success"):
        hospitals = result["data"]["hospitals"]
        print(f"Found {len(hospitals)} hospitals:")

        for i, hospital in enumerate(hospitals[:3], 1):
            print(f"\n{i}. {hospital.get('facility_name', 'N/A')}")
            print(f"   CCN: {hospital.get('ccn', 'N/A')}")
            print(
                f"   Location: {hospital.get('city', 'N/A')}, {hospital.get('state', 'N/A')}")

            # Show current rating if available
            if hospital.get("current_rating"):
                rating = hospital["current_rating"]
                overall = rating.get("overall_rating", "N/A")
                print(f"   Overall Rating: {overall} stars")

            # Show risk alerts if available
            if hospital.get("risk_alerts"):
                alerts = hospital["risk_alerts"]
                high_risk = [a for a in alerts if a.get("severity") == "HIGH"]
                if high_risk:
                    print(f"   ⚠️ High Risk Alerts: {len(high_risk)}")
    else:
        print(f"Search failed: {result.get('error', 'Unknown error')}")


def demo_enhanced_search():
    """Demonstrate enhanced search with Google Places integration"""
    print("\n🌟 ENHANCED SEARCH DEMO")
    print("-" * 40)

    client = SignumAPIClient()

    # Enhanced search
    print("Enhanced search for 'Medical Center'...")
    result = client.enhanced_hospital_search("Medical Center", limit=2)

    if result.get("success"):
        hospitals = result["data"]["hospitals"]
        print(f"Found {len(hospitals)} hospitals with enhanced data:")

        for i, hospital in enumerate(hospitals[:2], 1):
            print(f"\n{i}. {hospital.get('facility_name', 'N/A')}")
            print(
                f"   Location: {hospital.get('city', 'N/A')}, {hospital.get('state', 'N/A')}")

            # Show Google Places data if available
            if hospital.get("google_data"):
                google = hospital["google_data"]
                rating = google.get("rating", "N/A")
                reviews = google.get("user_rating_count", "N/A")
                print(f"   Google Rating: {rating}/5 ({reviews} reviews)")
                if google.get("phone"):
                    print(f"   Phone: {google['phone']}")
    else:
        print(
            f"Enhanced search failed: {result.get('error', 'Unknown error')}")


def demo_risk_analysis():
    """Demonstrate risk analysis functionality"""
    print("\n⚠️ RISK ANALYSIS DEMO")
    print("-" * 40)

    client = SignumAPIClient()

    # First, let's find a hospital to analyze
    result = client.search_hospitals(name="General", limit=1)

    if result.get("success") and result["data"]["hospitals"]:
        hospital = result["data"]["hospitals"][0]
        ccn = hospital.get("ccn")
        name = hospital.get("facility_name")

        if ccn:
            print(f"Analyzing risk for: {name} (CCN: {ccn})")

            risk_result = client.get_hospital_risk_analysis(ccn)

            if risk_result.get("success"):
                data = risk_result["data"]
                summary = data.get("summary", {})

                print(f"\nRisk Summary:")
                print(f"  High Risk Alerts: {summary.get('high_risk', 0)}")
                print(f"  Medium Risk Alerts: {summary.get('medium_risk', 0)}")
                print(f"  Low Risk Alerts: {summary.get('low_risk', 0)}")
                print(f"  Total Alerts: {summary.get('total_alerts', 0)}")

                # Show some example alerts
                alerts = data.get("alerts", [])
                high_alerts = [a for a in alerts if a.get(
                    "severity") == "HIGH"]

                if high_alerts:
                    print(f"\nHigh Risk Alerts:")
                    for alert in high_alerts[:2]:
                        domain = alert.get("domain", "N/A")
                        message = alert.get("message", "N/A")
                        print(f"  ⚠️ {domain}: {message}")
            else:
                print(
                    f"Risk analysis failed: {risk_result.get('error', 'Unknown error')}")
        else:
            print("No CCN available for risk analysis")
    else:
        print("Could not find a hospital for risk analysis demo")


def main():
    """Run all demos"""
    print("🏥 SIGNUM API Example Client")
    print("=" * 50)

    # Check API health first
    client = SignumAPIClient()
    health = client.health_check()

    if health.get("status") == "healthy":
        print("✅ API is healthy and ready!")

        # Run demos
        demo_provider_search()
        demo_hospital_search()
        demo_enhanced_search()
        demo_risk_analysis()

        print("\n" + "=" * 50)
        print("🎉 Demo completed!")
        print("\n💡 You can use this client as a starting point for your own applications.")
        print("📊 Full API documentation: http://localhost:8000/docs")

    else:
        print("❌ API is not healthy. Please check the server.")
        print("💡 Start the server with: ./start_api.sh")


if __name__ == "__main__":
    main()
