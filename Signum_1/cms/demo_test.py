"""
Demo Test - Simple demonstration of the new API features
"""

import os
import sys
import duckdb

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

def test_basic_search():
    """Test basic hospital search"""
    print("\n" + "="*60)
    print("DEMO: Basic Hospital Search")
    print("="*60)
    
    # Check if warehouse exists
    warehouse_dir = os.path.join(os.path.dirname(__file__), "..", "warehouse")
    db_path = os.path.join(warehouse_dir, "hospital.duckdb")
    
    if not os.path.exists(db_path):
        print("\n⚠️ Warehouse not found. Please run 'python -m cms.cli learn' first")
        return False
    
    try:
        # Connect to database
        con = duckdb.connect(db_path, read_only=True)
        
        # Get some hospitals
        result = con.execute("""
            SELECT DISTINCT ccn, facility_name, state, city
            FROM hospital_star
            ORDER BY release DESC
            LIMIT 5
        """).df()
        
        print(f"\n✅ Database Connected")
        print(f"   Found {len(result)} sample hospitals")
        
        print(f"\n📋 Sample Hospitals:")
        for i, row in result.iterrows():
            print(f"   {i+1}. {row['facility_name']} (CCN: {row['ccn']})")
            print(f"      Location: {row['city']}, {row['state']}")
        
        con.close()
        
        # Test search functionality
        print(f"\n🔍 Testing Search Functionality...")
        
        # Import modules
        sys.path.insert(0, os.path.dirname(__file__))
        
        from search_engine import HospitalSearchEngine
        from risk_analyzer import RiskAnalyzer
        from rating_comparator import RatingComparator
        
        # Create services
        search_engine = HospitalSearchEngine(warehouse_dir)
        risk_analyzer = RiskAnalyzer(warehouse_dir)
        rating_comparator = RatingComparator()
        
        # Search for hospitals
        results = search_engine.search_by_name("Mayo")
        
        if results:
            print(f"\n✅ Search Results: Found {len(results)} hospitals")
            
            # Get first hospital details
            first_hospital = results[0]
            ccn = first_hospital['ccn']
            
            print(f"\n🏥 Hospital Details:")
            print(f"   Name: {first_hospital.get('facility_name')}")
            print(f"   CCN: {ccn}")
            print(f"   Location: {first_hospital.get('city')}, {first_hospital.get('state')}")
            
            # Get latest rating
            rating = search_engine.get_latest_star_rating(ccn)
            print(f"   Latest Rating: {rating}")
            
            # Get domain metrics
            print(f"\n📊 Domain Metrics:")
            domain_metrics = risk_analyzer.get_domain_metrics(ccn)
            for domain, metrics in domain_metrics.items():
                if metrics:
                    value = metrics.get('latest_value')
                    if value is not None:
                        print(f"   {domain}: {value}")
            
            # Analyze risks
            print(f"\n⚠️ Risk Analysis:")
            alerts = risk_analyzer.analyze_all_risks(ccn)
            if alerts:
                for alert in alerts[:3]:  # Show first 3
                    print(f"   [{alert.get('severity')}] {alert.get('domain')}: {alert.get('message')}")
            else:
                print("   No risk alerts found")
            
            # Test rating comparison
            print(f"\n⭐ Rating Comparison Test:")
            google_rating = 4.8
            cms_rating = rating if rating else 4.5
            comparison = rating_comparator.compare_ratings(google_rating, cms_rating)
            
            print(f"   Google Rating: {google_rating}")
            print(f"   CMS Rating: {cms_rating}")
            print(f"   Difference: {comparison.get('difference'):.2f}")
            print(f"   Consistency: {comparison.get('consistency')}")
            print(f"   Analysis: {comparison.get('analysis')}")
            
        else:
            print("\n⚠️ No hospitals found matching 'Mayo'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_unified_service():
    """Test unified service"""
    print("\n" + "="*60)
    print("DEMO: Unified Service")
    print("="*60)
    
    try:
        from unified_service import UnifiedHospitalService
        
        # Create service
        warehouse_dir = os.path.join(os.path.dirname(__file__), "..", "warehouse")
        service = UnifiedHospitalService(warehouse_dir)
        
        # Search and evaluate
        print("\n🔍 Searching for hospitals...")
        result = service.search_and_evaluate("General", state=None)
        
        if "error" in result:
            print(f"   Error: {result['error']}")
            return False
        
        print(f"\n✅ Search Successful")
        print(f"   Found {len(result.get('search_results', []))} hospitals")
        
        if result.get('selected'):
            selected = result['selected']
            print(f"\n🎯 Selected Hospital:")
            print(f"   Name: {selected.get('facility_name')}")
            print(f"   CCN: {selected.get('ccn')}")
        
        # Get hospital data
        if result.get('selected'):
            ccn = result['selected']['ccn']
            print(f"\n📊 Fetching Detailed Data for CCN: {ccn}")
            
            data = service.get_hospital_data(ccn)
            
            print(f"\n📋 Basic Info:")
            basic = data.get('basic_info', {})
            print(f"   Facility: {basic.get('facility_name')}")
            print(f"   Current Rating: {basic.get('current_rating')}")
            
            print(f"\n📈 Insights:")
            insights = data.get('insights')
            if insights:
                print(f"   Trend: {insights.get('trend_direction')}")
                print(f"   Growth Index: {insights.get('growth_index')}")
            
            print(f"\n⚠️ Risk Alerts: {len(data.get('risk_alerts', []))}")
            
            # Show summary
            summary = service.get_summary(ccn)
            print(f"\n📝 Summary:")
            print(f"   {summary}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_demos():
    """Run all demo tests"""
    print("\n" + "="*80)
    print("DEMO TEST SUITE - New API Features")
    print("="*80)
    
    results = []
    
    # Test 1: Basic search
    results.append(("Basic Search", test_basic_search()))
    
    # Test 2: Unified service
    results.append(("Unified Service", test_unified_service()))
    
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
    run_all_demos()
