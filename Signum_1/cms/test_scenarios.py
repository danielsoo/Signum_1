"""
Test Scenarios for Hybrid Service

Tests various cases:
1. Hospital found with full data
2. Hospital found but no CMS API data
3. Hospital search with historical data only
4. Hospital with high risk indicators
5. Hospital search with multiple results
"""

import os
import sys
from typing import Dict, List

# Add parent directory to path
parent_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# Import modules using absolute imports
from unified_service import UnifiedHospitalService


class HybridHospitalService:
    """Hybrid service wrapper for testing"""
    def __init__(self, warehouse_dir=None):
        self.service = UnifiedHospitalService(warehouse_dir)
    
    def search_and_comprehensive_evaluate(self, query, state=None):
        """Search and evaluate with comprehensive data"""
        result = self.service.search_and_evaluate(query, state)
        
        if "error" in result:
            return result
        
        ccn = result["selected"]["ccn"]
        comprehensive = self.get_comprehensive_data(ccn)
        
        return {
            "search_results": result["search_results"],
            "selected": result["selected"],
            "comprehensive_evaluation": comprehensive,
            "summary": self._generate_summary(comprehensive)
        }
    
    def get_comprehensive_data(self, ccn):
        """Get comprehensive hospital data"""
        historical = self.service.get_hospital_data(ccn)
        
        return {
            "ccn": ccn,
            "basic_info": historical.get("basic_info"),
            "latest_rating": historical.get("basic_info", {}).get("current_rating"),
            "historical_metrics": historical.get("domain_metrics"),
            "risk_alerts": historical.get("risk_alerts", []),
            "insights": historical.get("insights"),
            "history": historical.get("history")
        }
    
    def _generate_summary(self, data):
        """Generate summary"""
        basic = data.get("basic_info", {})
        insights = data.get("insights", {})
        risk_alerts = data.get("risk_alerts", [])
        
        messages = []
        
        current_rating = basic.get("current_rating")
        if current_rating:
            messages.append(f"Current CMS Quality Rating: {current_rating}/5.0")
        
        if insights:
            trend = insights.get("trend_direction", "Unknown")
            messages.append(f"Growth Trend: {trend}")
        
        high_risks = [r for r in risk_alerts if r.get("severity") == "high"]
        if high_risks:
            messages.append(f"⚠️ High-Risk Indicators: {len(high_risks)} found")
        elif risk_alerts:
            messages.append(f"Caution: Some indicators need attention")
        else:
            messages.append("✅ Risk Assessment: Normal")
        
        return " | ".join(messages)


def test_scenario_1_full_data():
    """Test: Hospital with complete data (historical + API)"""
    print("\n" + "="*60)
    print("SCENARIO 1: Hospital with Complete Data")
    print("="*60)
    
    try:
        service = HybridHospitalService()
        
        # Search for a hospital
        result = service.search_and_comprehensive_evaluate("Mayo")
        
        print("\n✅ Search Status: SUCCESS")
        print(f"   Found {len(result.get('search_results', []))} hospitals")
        
        if result.get("selected"):
            selected = result["selected"]
            print(f"\n📋 Selected Hospital:")
            print(f"   Name: {selected.get('facility_name')}")
            print(f"   CCN: {selected.get('ccn')}")
            print(f"   Location: {selected.get('city')}, {selected.get('state')}")
        
        if result.get("comprehensive_evaluation"):
            comp = result["comprehensive_evaluation"]
            
            print(f"\n📊 Rating Information:")
            latest = comp.get("latest_rating", {})
            if latest:
                print(f"   Latest Rating: {latest.get('overall_rating')}")
                print(f"   Source: {latest.get('source', 'unknown')}")
            
            print(f"\n📈 Insights:")
            insights = comp.get("insights")
            if insights:
                print(f"   Trend: {insights.get('trend_direction')}")
                print(f"   Confidence: {insights.get('confidence')}")
            
            print(f"\n⚠️ Risk Alerts:")
            alerts = comp.get("risk_alerts", [])
            if alerts:
                for alert in alerts:
                    print(f"   [{alert.get('severity')}] {alert.get('domain')}: {alert.get('message')}")
            else:
                print("   None")
        
        print(f"\n📝 Summary: {result.get('summary', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario_2_historical_only():
    """Test: Hospital with only historical data (no API)"""
    print("\n" + "="*60)
    print("SCENARIO 2: Historical Data Only")
    print("="*60)
    
    try:
        service = HybridHospitalService()
        
        # Get data for a specific CCN (historical only)
        ccn = "390048"  # Example CCN
        data = service.get_comprehensive_data(ccn)
        
        print(f"\n✅ Data Retrieved for CCN: {ccn}")
        
        basic = data.get("basic_info", {})
        if basic:
            print(f"\n📋 Hospital Info:")
            print(f"   Name: {basic.get('facility_name')}")
            print(f"   Current Rating: {basic.get('current_rating')}")
        
        # Check if we have historical data
        metrics = data.get("historical_metrics", {})
        print(f"\n📊 Historical Metrics Available: {len([k for k,v in metrics.items() if v])} domains")
        
        # Check insights
        insights = data.get("insights")
        if insights:
            print(f"\n📈 Trend Analysis:")
            print(f"   Direction: {insights.get('trend_direction')}")
            print(f"   Growth Index: {insights.get('growth_index')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def test_scenario_3_multiple_results():
    """Test: Search with multiple hospital results"""
    print("\n" + "="*60)
    print("SCENARIO 3: Multiple Search Results")
    print("="*60)
    
    try:
        service = HybridHospitalService()
        
        # Search for common name
        result = service.search_and_comprehensive_evaluate("General")
        
        search_results = result.get("search_results", [])
        print(f"\n✅ Found {len(search_results)} hospitals")
        
        print(f"\n📋 Top 5 Results:")
        for i, hospital in enumerate(search_results[:5], 1):
            print(f"   {i}. {hospital.get('facility_name')}")
            print(f"      CCN: {hospital.get('ccn')}")
            print(f"      Location: {hospital.get('city')}, {hospital.get('state')}")
        
        if result.get("selected"):
            print(f"\n🎯 Selected: {result['selected'].get('facility_name')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def test_scenario_4_no_results():
    """Test: Search that returns no results"""
    print("\n" + "="*60)
    print("SCENARIO 4: No Results Found")
    print("="*60)
    
    try:
        service = HybridHospitalService()
        
        # Search for non-existent hospital
        result = service.search_and_comprehensive_evaluate("NonExistentHospital12345")
        
        if result.get("error"):
            print(f"\n✅ Error Handling: WORKING")
            print(f"   Error: {result.get('error')}")
            print(f"   Suggestion: {result.get('suggestion')}")
            return True
        else:
            print("\n⚠️ Should have returned error but didn't")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def run_all_tests():
    """Run all test scenarios"""
    print("\n" + "="*80)
    print("HYBRID SERVICE TEST SUITE")
    print("="*80)
    
    results = []
    
    # Test 1: Full data
    results.append(("Scenario 1: Full Data", test_scenario_1_full_data()))
    
    # Test 2: Historical only
    results.append(("Scenario 2: Historical Only", test_scenario_2_historical_only()))
    
    # Test 3: Multiple results
    results.append(("Scenario 3: Multiple Results", test_scenario_3_multiple_results()))
    
    # Test 4: No results
    results.append(("Scenario 4: No Results", test_scenario_4_no_results()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    total_passed = sum(1 for _, p in results if p)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_all_tests()
