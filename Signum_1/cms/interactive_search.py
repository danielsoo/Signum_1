"""
Interactive Hospital Search with Google + NPPES + CMS Integration
All comments and output in English
"""

from __future__ import annotations
import os
import re
from typing import Optional, Dict, Any, List
import os
import sys

# Global cache for risk analysis (in-memory only)
_risk_cache = {}

# Helper to ask user for input
def ask(prompt: str, default: str = "") -> str:
    """Prompt user for input"""
    s = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return s if s else default


def show_action_menu() -> str:
    """Show back/exit menu and return user choice"""
    print("\n" + "-"*70)
    print("What would you like to do?")
    print("1. Go back (return to main menu)")
    print("2. Exit")
    print("-"*70)
    
    choice = ask("Select (1-2)", "1")
    
    if choice == "1":
        return "back"
    elif choice == "2":
        return "exit"
    else:
        return "back"


def search_interactive(warehouse_dir: str) -> None:
    """
    Interactive hospital search with comprehensive evaluation
    
    Flow:
    1. Get user input (name, location, specialty, etc.)
    2. Search Google Places
    3. Verify with NPPES
    4. Get CMS data
    5. Show comprehensive results
    """
    print("\n" + "="*70)
    print("🏥 Integrated Hospital Search System")
    print("="*70 + "\n")
    
    while True:
        # Get search type
        print("Select search type:")
        print("1. Hospital search")
        print("2. Doctor search")
        print("3. Hospitals by location")
        print("4. Hospitals by specialty")
        print("5. Exit")
        
        search_type = ask("Select (1-5)", "1")
        
        if search_type == "1":
            result = search_hospital_interactive(warehouse_dir)
        elif search_type == "2":
            result = search_doctor_interactive(warehouse_dir)
        elif search_type == "3":
            result = search_by_location(warehouse_dir)
        elif search_type == "4":
            result = search_by_specialty(warehouse_dir)
        elif search_type == "5":
            print("Goodbye!")
            break
        else:
            print("❌ Invalid selection")
            result = "back"
        
        # Handle result: back or exit
        if result == "exit":
            print("Goodbye!")
            break
        elif result == "back":
            # Just continue the loop (return to main menu)
            continue


def search_hospital_interactive(warehouse_dir: str) -> str:
    """Interactive hospital search - returns 'back' or 'exit'"""
    from .search_engine import HospitalSearchEngine
    from .risk_analyzer import RiskAnalyzer
    from .rating_comparator import RatingComparator
    
    # Get user input
    print("\nEnter hospital information:")
    hospital_name = ask("Hospital name")
    city = ask("City")
    state = ask("State (2 letters, e.g., CA, NY)")
    postal = ask("Postal code")
    
    # Build search query
    query_parts = []
    if hospital_name:
        query_parts.append(hospital_name)
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    if postal:
        query_parts.append(postal)
    
    search_query = " ".join(query_parts)
    
    if not search_query:
        print("❌ Please enter at least one piece of information")
        return show_action_menu()
    
    print(f"\n1️⃣ Searching Google Places: '{search_query}'")
    
    # Try Google search
    google_results = try_google_search(search_query)
    
    if not google_results:
        print("❌ Google search failed, trying NPPES...")
        nppes_results = try_nppes_search(hospital_name, city, state, warehouse_dir)
        
        if nppes_results:
            print(f"✅ NPPES search successful: {len(nppes_results)} hospitals found")
            show_nppes_only_results(nppes_results, warehouse_dir)
        else:
            print("❌ No results found")
        
        return show_action_menu()
    
    print(f"✅ Google: {len(google_results)} hospitals found")
    
    # Verify with NPPES
    print(f"\n2️⃣ Verifying with NPPES...")
    validated_results = []
    
    for google_hospital in google_results:
        ccn = verify_nppes_for_hospital(google_hospital, warehouse_dir)
        
        if ccn:
            validated_results.append({
                "google": google_hospital,
                "ccn": ccn
            })
        else:
            validated_results.append({
                "google": google_hospital,
                "ccn": None,
                "note": "Google only (NPPES unverified)"
            })
    
    print(f"✅ NPPES verification complete: {len([r for r in validated_results if r.get('ccn')])} hospitals verified")
    
    # Get CMS data
    print(f"\n3️⃣ Retrieving CMS quality data...")
    
    for result in validated_results:
        if result.get('ccn'):
            ccn = result['ccn']
            cms_data = get_cms_comprehensive_data(ccn, warehouse_dir)
            result['cms'] = cms_data
    
    # Show results - 3번 스타일의 상세 출력 사용
    print(f"\n" + "="*70)
    print(f"Search Results: {len(validated_results)} hospitals found")
    print("="*70 + "\n")
    
    # 결과를 3번 스타일 포맷으로 변환
    from .search_engine import HospitalSearchEngine
    search_engine = HospitalSearchEngine(warehouse_dir)
    
    display_results = []
    for result in validated_results[:10]:
        google = result['google']
        ccn = result.get('ccn')
        
        if not ccn:
            continue  # CCN이 없으면 스킵
        
        # NPI 조회 (양방향 검증 생략)
        npi = None
        try:
            npi = get_npi_for_hospital(google['name'], None)
        except Exception:
            pass
        
        # CMS 정보 가져오기
        cms_info = search_engine.get_cms_rating_with_source(ccn)
        
        # 정신병원 체크
        psych_indicators = None
        if cms_info.get('rating') is None:
            psych_indicators = search_engine.get_psychiatric_quality_indicators(ccn)
        
        hospital_data = {
            'facility_name': google['name'],
            'ccn': ccn,
            'npi': npi,
            'npi_verification': None,  # 검증 정보는 더 이상 표시하지 않음
            'google_address': google.get('address'),
            'city': None,  # Google 주소 사용
            'state': None,
            'zip': None,
            'cms_rating': cms_info.get('rating'),
            'cms_source': cms_info.get('source'),
            'cms_confidence': cms_info.get('confidence'),
            'cms_reason': cms_info.get('reason'),
            'psychiatric_indicators': psych_indicators,
            'google_rating': google.get('rating'),
            'google_reviews': google.get('user_rating_count'),
            'distance': float('inf')
        }
        
        display_results.append(hospital_data)
    
    # 3번 스타일로 출력
    _display_hospital_results(display_results, 0)
    
    return show_action_menu()


def try_google_search(query: str) -> List[Dict]:
    """Try to search Google Places using free_provider_apis"""
    try:
        # 오프라인 모드면 바로 우회
        if os.getenv("FREE_APIS_OFFLINE") == "1":
            return []
        import sys
        from pathlib import Path
        
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists():
            return []
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception as e:
                print(f"⚠️ Failed to load .env: {e}")
        
        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))
        
        from free_provider_apis.google.places_client_v1 import PlacesV1Client
        from free_provider_apis.google.feature_flags import enable
        
        enable("text_search")
        client = PlacesV1Client(strict=False)
        
        result = client.search_text(
            query,
            fields=[
                "places.id",
                "places.displayName",
                "places.formattedAddress", 
                "places.location",
                "places.rating",
                "places.userRatingCount"
            ]
        )
        
        places = result.get("places", [])
        
        hospitals = []
        for place in places:
            name = place.get("displayName", {}).get("text", "")
            types = place.get("types", [])
            
            hospital_keywords = ["hospital", "medical", "center", "clinic", "health"]
            is_hospital = any(kw in name.lower() for kw in hospital_keywords)
            
            if is_hospital:
                hospitals.append({
                    "name": name,
                    "address": place.get("formattedAddress"),
                    "rating": place.get("rating"),
                    "user_rating_count": place.get("userRatingCount"),
                    "location": place.get("location"),
                    "place_id": place.get("id")
                })
        
        return hospitals
        
    except Exception as e:
        print(f"⚠️ Google search error: {e}")
        return []


def try_nppes_search(name: str, city: str, state: str, warehouse_dir: str) -> List[Dict]:
    """Search NPPES directly when Google fails"""
    try:
        # 오프라인 모드면 DuckDB 로컬 탐색으로 바로 우회
        if os.getenv("FREE_APIS_OFFLINE") == "1":
            from .search_engine import HospitalSearchEngine
            search_engine = HospitalSearchEngine(warehouse_dir)
            results = []
            if name:
                results = search_engine.search_by_name(name, state)
            if not results and city:
                results = search_engine.search_by_address(city, state)
            return results
        import sys
        from pathlib import Path
        
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists():
            from .search_engine import HospitalSearchEngine
            search_engine = HospitalSearchEngine(warehouse_dir)
            results = []
            if name:
                results = search_engine.search_by_name(name, state)
            if not results and city:
                results = search_engine.search_by_address(city, state)
            return results
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception as e:
                print(f"⚠️ Failed to load .env: {e}")
        
        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))
        
        from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient
        
        nppes_client = NPPESClient()
        cms_pdc = CMSPDCClient()
        results = []
        
        if name:
            nppes_result = nppes_client.search(
                organization_name=name,
                state=state if state else None,
                city=city if city else None,
                limit=10
            )
            
            items = NPPESClient.normalize(nppes_result)
            
            for item in items:
                npi = item.get("npi")
                if npi:
                    affils = cms_pdc.get_hospital_affiliations_by_npi(npi)
                    if affils:
                        for affil in affils:
                            ccn = affil.get("ccn")
                            if ccn:
                                results.append({
                                    "ccn": ccn,
                                    "facility_name": item.get("name", ""),
                                    "city": "",
                                    "state": state if state else ""
                                })
        
        if not results:
            from .search_engine import HospitalSearchEngine
            search_engine = HospitalSearchEngine(warehouse_dir)
            if name:
                results = search_engine.search_by_name(name, state)
            if not results and city:
                results = search_engine.search_by_address(city, state)
        
        return results
        
    except Exception as e:
        print(f"⚠️ NPPES search error: {e}")
        from .search_engine import HospitalSearchEngine
        search_engine = HospitalSearchEngine(warehouse_dir)
        results = []
        if name:
            results = search_engine.search_by_name(name, state if state else None)
        if not results and city:
            results = search_engine.search_by_address(city, state)
        return results


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    두 병원명의 유사도 계산 (0.0 ~ 1.0)
    """
    if not name1 or not name2:
        return 0.0
    
    # 소문자 변환 및 공통 단어 제거
    n1 = name1.lower().replace('hospital', '').replace('medical center', '').replace('health system', '').strip()
    n2 = name2.lower().replace('hospital', '').replace('medical center', '').replace('health system', '').strip()
    
    # 단어 집합으로 비교
    words1 = set(n1.split())
    words2 = set(n2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def verify_npi_ccn_match(npi: str, ccn: str, facility_name: str, state: str) -> Dict[str, Any]:
    """
    NPI와 CCN이 같은 병원을 가리키는지 양방향 검증
    
    Returns:
        {
            "verified": True/False,
            "confidence": "high"/"medium"/"low"/"none",
            "npi_name": "...",
            "ccn_name": "...",
            "match_score": 0.95,
            "warnings": [...]
        }
    """
    result = {
        "verified": False,
        "confidence": "none",
        "npi_name": None,
        "ccn_name": facility_name,
        "match_score": 0.0,
        "warnings": []
    }
    
    try:
        # Offline 모드이면 검증 불가
        if os.getenv("FREE_APIS_OFFLINE") == "1":
            result["warnings"].append("Offline mode - verification skipped")
            return result
        
        from pathlib import Path
        import sys
        
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists():
            result["warnings"].append("NPPES API not available")
            return result
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception:
                pass
        
        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))
        
        from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient
        
        nppes_client = NPPESClient()
        cms_pdc_client = CMSPDCClient()
        
        # 1. NPI → CCN 검증 (CMS PDC API 사용)
        ccn_match = False
        try:
            affiliations = cms_pdc_client.get_hospital_affiliations_by_npi(npi)
            for affil in affiliations:
                affil_ccn = affil.get("ccn") if isinstance(affil, dict) else None
                if affil_ccn == ccn:
                    ccn_match = True
                    result["verified"] = True
                    result["confidence"] = "high"
                    break
        except Exception as e:
            result["warnings"].append(f"CMS PDC lookup failed: {str(e)[:50]}")
        
        # 2. NPI로 NPPES에서 병원명 조회
        try:
            nppes_result = nppes_client.search(npi=npi, limit=1)
            items = NPPESClient.normalize(nppes_result)
            
            if items:
                npi_name = items[0].get("organization_name") or items[0].get("name")
                result["npi_name"] = npi_name
                
                # 이름 유사도 계산
                if npi_name:
                    similarity = calculate_name_similarity(npi_name, facility_name)
                    result["match_score"] = similarity
                    
                    # 이미 CCN 매칭이 확인되었으면 high
                    if ccn_match:
                        result["confidence"] = "high"
                    # CCN 매칭은 실패했지만 이름이 매우 유사하면 medium
                    elif similarity >= 0.7:
                        result["verified"] = True
                        result["confidence"] = "medium"
                    elif similarity >= 0.4:
                        result["confidence"] = "low"
                        result["warnings"].append(f"Name differs: '{npi_name}' vs '{facility_name}'")
                    else:
                        result["confidence"] = "none"
                        result["warnings"].append(f"Name mismatch: '{npi_name}' vs '{facility_name}'")
        except Exception as e:
            result["warnings"].append(f"NPPES lookup failed: {str(e)[:50]}")
        
        return result
        
    except Exception as e:
        result["warnings"].append(f"Verification error: {str(e)[:50]}")
        return result


def get_npi_for_hospital(facility_name: str, state: Optional[str] = None) -> Optional[str]:
    """
    병원명과 주로 NPPES에서 NPI 번호를 조회
    
    Returns:
        NPI 번호 (문자열) 또는 None
    """
    try:
        # Offline 모드이거나 free_apis가 없으면 None 반환
        if os.getenv("FREE_APIS_OFFLINE") == "1":
            return None
        
        from pathlib import Path
        import sys
        
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists():
            return None
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception:
                pass
        
        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))
        
        from free_provider_apis.government.clients_free import NPPESClient
        
        nppes_client = NPPESClient()
        
        # NPPES에서 병원명으로 검색
        search_params = {"organization_name": facility_name, "limit": 3}
        if state:
            search_params["state"] = state
        
        nppes_result = nppes_client.search(**search_params)
        items = NPPESClient.normalize(nppes_result)
        
        # 첫 번째 매치를 반환 (이름이 가장 유사한 것)
        if items:
            return items[0].get("npi")
        
        return None
        
    except Exception:
        return None


def verify_nppes_for_hospital(google_hospital: Dict, warehouse_dir: str) -> Optional[str]:
    """Verify hospital via NPPES → CMS PDC and resolve CCN"""
    from .search_engine import HospitalSearchEngine

    hospital_name = google_hospital.get('name', '')
    address = google_hospital.get('address', '') or ''

    search_engine = HospitalSearchEngine(warehouse_dir)

    # Try to extract city/state hints from the formatted address
    city_hint: Optional[str] = None
    state_hint: Optional[str] = None
    if address:
        parts = [p.strip() for p in address.split(',') if p.strip()]
        if len(parts) >= 2:
            city_hint = parts[-3] if len(parts) >= 3 else parts[-2]
            state_part = parts[-2] if len(parts) >= 2 else ''
            m = re.search(r'\b([A-Z]{2})\b', state_part)
            if m:
                state_hint = m.group(1)

    def _resolve_ccn_locally(candidate_names: List[str]) -> Optional[str]:
        """Resolve CCN using local DuckDB searches."""
        names = [n for n in candidate_names if n]
        for cand in names:
            results = search_engine.search_by_name(cand, state_hint)
            if results:
                if city_hint:
                    for r in results:
                        if (r.get('city') or '').lower() == city_hint.lower():
                            return r['ccn']
                return results[0]['ccn']

        if city_hint:
            addr_results = search_engine.search_by_address(city_hint, state_hint)
            if addr_results:
                if hospital_name:
                    for r in addr_results:
                        if (r.get('facility_name') or '').lower().startswith(hospital_name.lower()[:10]):
                            return r['ccn']
                return addr_results[0]['ccn']

        return None

    try:
        from pathlib import Path
        import sys

        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"

        # Offline mode or missing free apis → fall back to local search immediately
        if os.getenv("FREE_APIS_OFFLINE") == "1" or not free_apis_path.exists():
            return _resolve_ccn_locally([hospital_name])

        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception as e:
                print(f"⚠️ Failed to load .env: {e}")

        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))

        from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient

        nppes_client = NPPESClient()
        cms_pdc_client = CMSPDCClient()

        nppes_result = nppes_client.search(organization_name=hospital_name, limit=5)
        items = NPPESClient.normalize(nppes_result)

        candidate_names: List[str] = [hospital_name]

        for item in items:
            npi = item.get("npi")
            if not npi:
                continue

            affils = cms_pdc_client.get_hospital_affiliations_by_npi(npi)
            for affil in affils:
                ccn = affil.get("ccn") if isinstance(affil, dict) else None
                if ccn:
                    return ccn

                affil_name = None
                if isinstance(affil, dict):
                    affil_name = affil.get("hospital_name") or affil.get("name")

                if affil_name and affil_name not in candidate_names:
                    candidate_names.append(affil_name)

        # If we reach here, resolve locally using gathered names
        resolved = _resolve_ccn_locally(candidate_names)
        if resolved:
            return resolved

        return None

    except Exception:
        return _resolve_ccn_locally([hospital_name])


def get_cms_comprehensive_data(ccn: str, warehouse_dir: str) -> Dict:
    """Get comprehensive CMS data for a hospital"""
    from .search_engine import HospitalSearchEngine
    from .risk_analyzer import RiskAnalyzer
    from .rating_comparator import RatingComparator
    
    search_engine = HospitalSearchEngine(warehouse_dir)
    risk_analyzer = RiskAnalyzer(warehouse_dir)
    
    hospital_info = search_engine.get_by_ccn(ccn)
    
    # 공식/예측/추정 순서로 출처 포함 조회
    rating_info = search_engine.get_cms_rating_with_source(ccn)
    rating = rating_info.get('rating')
    source = rating_info.get('source')
    confidence = rating_info.get('confidence')
    reason = rating_info.get('reason')
    is_predicted = (source == 'predicted')
    is_estimated = (source == 'estimated')
    prediction_info = search_engine.get_predicted_star_rating(ccn) if is_predicted else None
    
    alerts = risk_analyzer.analyze_all_risks(ccn)
    metrics = risk_analyzer.get_domain_metrics(ccn)
    
    return {
        "hospital_info": hospital_info,
        "rating": rating,
        "is_predicted": is_predicted,
        "prediction_info": prediction_info,
        "alerts": alerts,
        "metrics": metrics,
        "history": rating,
        "is_estimated": is_estimated,
        "source": source,
        "confidence": confidence,
        "reason": reason
    }


def show_nppes_only_results(results: List[Dict], warehouse_dir: str) -> None:
    """Show results when only NPPES data is available"""
    print("\n" + "="*70)
    print(f"NPPES Search Results: {len(results)} hospitals")
    print("="*70 + "\n")
    
    # 3번 스타일로 출력하기 위해 데이터 변환
    from .search_engine import HospitalSearchEngine
    search_engine = HospitalSearchEngine(warehouse_dir)
    
    display_results = []
    for hospital in results[:10]:
        ccn = hospital['ccn']
        
        # NPI 조회 (양방향 검증 생략)
        npi = None
        try:
            npi = get_npi_for_hospital(hospital['facility_name'], hospital.get('state'))
        except Exception:
            pass
        
        # CMS 정보 가져오기
        cms_info = search_engine.get_cms_rating_with_source(ccn)
        
        # 정신병원 체크
        psych_indicators = None
        if cms_info.get('rating') is None:
            psych_indicators = search_engine.get_psychiatric_quality_indicators(ccn)
        
        hospital_data = {
            'facility_name': hospital['facility_name'],
            'ccn': ccn,
            'npi': npi,
            'npi_verification': None,
            'google_address': None,
            'city': hospital.get('city'),
            'state': hospital.get('state'),
            'zip': hospital.get('zip'),
            'cms_rating': cms_info.get('rating'),
            'cms_source': cms_info.get('source'),
            'cms_confidence': cms_info.get('confidence'),
            'cms_reason': cms_info.get('reason'),
            'psychiatric_indicators': psych_indicators,
            'google_rating': None,
            'google_reviews': None,
            'distance': float('inf')
        }
        
        display_results.append(hospital_data)
    
    # 3번 스타일로 출력
    _display_hospital_results(display_results, 0)
    
    if len(results) > 0:
        show_detailed_analysis_for_ccn(results[0]['ccn'], warehouse_dir)


def show_detailed_analysis_for_ccn(ccn: str, warehouse_dir: str) -> None:
    """Show detailed analysis for a CCN"""
    cms_data = get_cms_comprehensive_data(ccn, warehouse_dir)
    
    hospital_info = cms_data['hospital_info']
    rating = cms_data['rating']
    alerts = cms_data['alerts']
    metrics = cms_data['metrics']
    
    print("\n" + "="*70)
    print(f"Detailed Analysis: {hospital_info.get('facility_name')}")
    print("="*70 + "\n")
    
    print("📊 Summary Information")
    print(f"  - CCN: {ccn}")
    if rating:
        if cms_data.get('is_predicted'):
            prediction_info = cms_data.get('prediction_info', {})
            confidence = cms_data.get('confidence') or prediction_info.get('confidence')
            conf_text = f", 신뢰도: {confidence:.1%}" if confidence is not None else ""
            print(f"  - CMS Quality: ⭐ {rating}/5.0 (AI 예측{conf_text})")
            
            # 예측 상세 정보 표시 (선택적)
            if prediction_info.get('markov_prediction') and prediction_info.get('regression_prediction'):
                print(f"    • Markov 예측: {prediction_info['markov_prediction']:.2f}")
                print(f"    • Regression 예측: {prediction_info['regression_prediction']:.2f}")
        elif cms_data.get('is_estimated'):
            print(f"  - CMS Quality: ⭐ {rating}/5.0 (Estimated)")
        else:
            print(f"  - CMS Quality: ⭐ {rating}/5.0 (Official)")
    else:
        reason = cms_data.get('reason') or 'N/A'
        print(f"  - CMS Quality: N/A ({reason})")
    print()
    
    # 각 도메인의 기여도 계산 및 표시
    domain_contributions = calculate_domain_contributions(metrics, rating)
    if domain_contributions:
        print("📊 Domain Contributions (별점 구성 요소 비중)")
        for domain, percentage in sorted(domain_contributions.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {domain}: {percentage:.1f}%")
        print()
    
    print("📈 Domain Performance (with units)")
    for domain, data in metrics.items():
        if data and data.get('latest_value') is not None:
            value = data['latest_value']
            unit = get_domain_unit(domain, data.get('measure_name'))
            print(f"  - {domain}: {value:.2f} {unit}")
    print()
    
    print("⚠️ Risk Analysis")
    high_risks = [a for a in alerts if a.get('severity') == 'high']
    if high_risks:
        print(f"  - High-risk indicators: {len(high_risks)} found")
        for alert in high_risks:
            print(f"    • {alert['message']}")
    else:
        print("  - High-risk indicators: None")
    print()


def calculate_domain_contributions(metrics: Dict, rating: Optional[float]) -> Dict[str, float]:
    """
    각 도메인이 별점에 기여하는 비중 계산 (퍼센트)
    
    CMS 별점은 5개 도메인으로 구성되며, 각 도메인의 가중치는 다음과 같습니다:
    - Mortality (사망률): 22%
    - Readmission (재발율): 22%
    - Safety (안전): 22%
    - PatientExperience (환자 경험): 22%
    - Timely (시기 적절성): 12%
    
    실제 데이터 유무와 성과를 고려하여 조정합니다.
    
    Args:
        metrics: 각 도메인의 메트릭 데이터
        rating: CMS 별점 (1-5)
    
    Returns:
        {domain: percentage} 형태의 딕셔너리 (합계 100%)
    """
    if not metrics:
        return {}
    
    # CMS 공식 별점 계산 가중치 (실제 CMS 기준)
    # 참고: CMS는 복잡한 계산식을 사용하지만, 일반적으로는 다음과 같은 비중
    base_weights = {
        "Mortality": 0.22,           # 22%
        "Readmission": 0.22,         # 22%
        "Safety": 0.22,              # 22%
        "PatientExperience": 0.22,   # 22%
        "Timely": 0.12               # 12%
    }
    
    # 각 도메인의 데이터 유무와 성과를 고려한 조정 가중치
    adjusted_weights = {}
    total_weight = 0
    
    for domain, base_weight in base_weights.items():
        domain_data = metrics.get(domain)
        
        if domain_data and domain_data.get('latest_value') is not None:
            # 데이터가 있는 도메인은 기본 가중치 유지 또는 약간 조정
            # 성과가 좋을수록(별점에 긍정적 기여) 약간의 보너스 가중치
            value = domain_data.get('latest_value', 0)
            national_compare = domain_data.get('national_comparison', '')
            
            # 국가 평균보다 좋으면(Below 또는 Same) 가중치 약간 증가
            if national_compare in ['Below', 'Same']:
                adjusted_weight = base_weight * 1.1  # 10% 보너스
            else:
                adjusted_weight = base_weight
            
            adjusted_weights[domain] = adjusted_weight
            total_weight += adjusted_weight
        else:
            # 데이터가 없는 도메인은 가중치를 0으로 (또는 매우 낮게)
            adjusted_weights[domain] = base_weight * 0.1  # 10%만 반영
            total_weight += adjusted_weights[domain]
    
    # 정규화하여 합이 100%가 되도록 변환
    if total_weight > 0:
        percentages = {k: (v / total_weight * 100) for k, v in adjusted_weights.items()}
        return percentages
    
    return {}


def get_domain_unit(domain: str, measure_name: Optional[str] = None) -> str:
    """Get appropriate unit for domain metric"""
    units = {
        "Mortality": "deaths per 100 patients",
        "Readmission": "% re-admission rate",
        "Safety": "complications per 1,000 patients",
        "PatientExperience": "% satisfaction score",
        "Timely": "% timely delivery rate"
    }
    return units.get(domain, "measure-specific unit")


def show_google_only_result(google_hospital: Dict) -> None:
    """Show result when only Google data is available"""
    print("\n" + "⚠️"*35)
    print("⚠️ This hospital is registered on Google Maps but not in NPPES")
    print("⚠️"*35 + "\n")
    
    print("📊 Available Information:")
    print(f"  - Location: {google_hospital.get('address')}")
    print(f"  - Google Rating: {google_hospital.get('rating')}/5.0")
    if google_hospital.get('user_rating_count'):
        print(f"  - Reviews: {google_hospital.get('user_rating_count')}")


def search_doctor_interactive(warehouse_dir: str) -> str:
    """Search for doctors and their affiliated hospitals - returns 'back' or 'exit'"""
    
    print("\nEnter doctor information:")
    
    first_name = ask("First Name")
    last_name = ask("Last Name")
    specialty = ask("Specialty (e.g., Cardiology)")
    state = ask("State (2 letters, e.g., PA, NY)")
    
    if not last_name and not first_name:
        print("❌ Please enter at least a name")
        return show_action_menu()
    
    print(f"\n👨‍⚕️ Searching NPPES API...")
    
    try:
        import sys
        from pathlib import Path
        
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists():
            print("❌ free_provider_apis not found")
            return show_action_menu()
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception as e:
                print(f"⚠️ Failed to load .env: {e}")
        
        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))
        
        from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient
        
        nppes_client = NPPESClient()
        cms_pdc = CMSPDCClient()
        
        search_params = {}
        if first_name:
            search_params['first_name'] = first_name
        if last_name:
            search_params['last_name'] = last_name
        if specialty:
            search_params['taxonomy_description'] = specialty
        if state:
            search_params['state'] = state.upper()
        
        raw_result = nppes_client.search(**search_params, limit=10)
        items = NPPESClient.normalize(raw_result)
        
        if not items:
            print("❌ No results found")
            return show_action_menu()
        
        print(f"✅ Found {len(items)} doctors\n")
        
        for i, doctor in enumerate(items[:5], 1):
            print(f"\n{'='*70}")
            print(f"Doctor {i}: {doctor.get('name', 'Unknown')}")
            
            if doctor.get('npi'):
                print(f"NPI: {doctor.get('npi')}")
            
            if doctor.get('primary_taxonomy'):
                tax = doctor.get('primary_taxonomy')
                if tax and tax.get('desc'):
                    print(f"Specialty: {tax['desc']}")
            
            if doctor.get('practice_addresses'):
                addr = doctor['practice_addresses'][0]
                print(f"Address: {addr.get('address_1', '')}")
                if addr.get('city') and addr.get('state'):
                    print(f"         {addr.get('city')}, {addr.get('state')}")
            
            if doctor.get('npi'):
                npi = doctor['npi']
                print(f"\n🏥 Searching affiliated hospitals...")
                
                affils = cms_pdc.get_hospital_affiliations_by_npi(npi)
                if affils:
                    ccns = [a['ccn'] for a in affils if a.get('ccn')]
                    if ccns:
                        hospital_data = cms_pdc.get_hospital_quality_by_ccns(tuple(ccns))
                        
                        print(f"   Found {len(ccns)} hospitals:")
                        for ccn in ccns:
                            if ccn in hospital_data:
                                hosp = hospital_data[ccn]
                                name = hosp.get('hospital_name', 'Unknown')
                                rating = hosp.get('overall_rating', 'N/A')
                                print(f"\n   - {name} [CCN: {ccn}]")
                                if rating and rating != 'N/A':
                                    stars = "⭐" * int(float(rating))
                                    print(f"     CMS Rating: {stars} {rating}/5.0")
                else:
                    print("   No hospital affiliations found")
            
            print()
    
    except Exception as e:
        print(f"⚠️ Error: {e}")
    
    return show_action_menu()


def ask_int(prompt: str, default: int) -> int:
    """Ask user for integer input"""
    try:
        s = input(f"{prompt} [{default}]: ").strip()
        if s:
            return int(s)
        return default
    except ValueError:
        return default


def search_by_location(warehouse_dir: str) -> str:
    """Search hospitals by location with filters - returns 'back' or 'exit'"""
    
    print("\nSet location filters:")
    
    state = ask("State (required)", "")
    city = ask("City")
    
    if not state:
        print("❌ State is required")
        return show_action_menu()
    
    from .search_engine import HospitalSearchEngine
    search_engine = HospitalSearchEngine(warehouse_dir)
    
    # Step 1: 먼저 병원 수 확인
    total_count = search_engine.count_hospitals_by_address(city or "", state)
    
    if total_count == 0:
        print(f"❌ No hospitals found in {state}")
        return show_action_menu()
    
    print(f"\n📊 Found {total_count} hospitals in {state}")
    
    # Step 2: Adaptive loading strategy
    THRESHOLD = 5000
    use_pagination = total_count > THRESHOLD
    
    if use_pagination:
        print(f"   (Loading page by page due to large result set)")
        return _search_by_location_paginated(warehouse_dir, search_engine, city, state, total_count)
    else:
        print(f"   (Loading all results)")
        return _search_by_location_full(warehouse_dir, search_engine, city, state, total_count)


def _search_by_location_full(warehouse_dir: str, search_engine, city: str, 
                             state: str, total_count: int) -> str:
    """옵션 A: 전체 병원 로드 (메모리 캐싱)"""
    
    # 전체 병원 리스트 로드 (이미 정렬됨)
    all_results = search_engine.search_by_address(city or "", state)
    
    if not all_results:
        print(f"❌ No hospitals found")
        return show_action_menu()
    
    # 사용자 위치 입력 (optional)
    print("\nEnter your location for distance sorting (optional):")
    user_city = ask("City", "")
    user_state = ask("State", "")
    user_coords = _get_user_coordinates(user_city, user_state)
    
    # 정렬 옵션
    print("\nSorting options:")
    print("1. CMS rating (highest first)")
    print("2. Google rating (highest first)")
    print("3. Distance")
    sort_option = ask("Sort by (1-3)", "1")
    
    # 페이지네이션 상태
    page_size = 20
    current_page = 0
    google_fetched_up_to = 0
    
    while True:
        start_idx = current_page * page_size
        end_idx = start_idx + page_size
        
        if start_idx >= len(all_results):
            print("📋 마지막 페이지입니다.")
            current_page = max(0, current_page - 1)
            continue
        
        page_results = all_results[start_idx:end_idx]
        
        # CMS 정보 및 Google 정보 수집 (처음 보는 병원들만)
        _enrich_hospital_data(page_results, start_idx, end_idx, all_results, 
                             google_fetched_up_to, search_engine, city, state, user_coords)
        google_fetched_up_to = max(google_fetched_up_to, min(end_idx, len(all_results)))
        
        # 정렬 (전체 리스트 기준)
        if sort_option == "1":
            all_results = sorted(all_results, 
                               key=lambda x: (x.get('cms_rating') is None, -(x.get('cms_rating') or 0)))
        elif sort_option == "2":
            all_results = sorted(all_results,
                               key=lambda x: (x.get('google_rating') is None, -(x.get('google_rating') or 0)))
        elif sort_option == "3":
            all_results = sorted(all_results, key=lambda x: x.get('distance', float('inf')))
        
        # 재조정된 인덱스로 페이지 가져오기
        page_results = all_results[start_idx:end_idx]
        
        # 결과 출력
        print(f"\nShowing {start_idx+1}-{min(end_idx, len(all_results))} of {len(all_results)} hospitals")
        print("="*70 + "\n")
        
        _display_hospital_results(page_results, start_idx)
        
        # 메뉴
        print("\n" + "-"*70)
        print("What would you like to do?")
        print("1. 더 보기")
        print("2. 뒤로가기")
        print("3. 나가기")
        print("-"*70)
        
        choice = ask("Select (1-3)", "2")
        
        if choice == "1":
            if end_idx >= len(all_results):
                print("📋 마지막 페이지입니다.")
                continue
            current_page += 1
        elif choice == "2":
            return "back"
        else:
            return "exit"


def _search_by_location_paginated(warehouse_dir: str, search_engine, city: str,
                                  state: str, total_count: int) -> str:
    """옵션 B: 페이지별 병원 로드 (OFFSET/LIMIT)"""
    
    # 사용자 위치 입력 (optional)
    print("\nEnter your location for distance sorting (optional):")
    user_city = ask("City", "")
    user_state = ask("State", "")
    user_coords = _get_user_coordinates(user_city, user_state)
    
    # 정렬 옵션
    print("\nSorting options:")
    print("1. CMS rating (highest first)")
    print("2. Google rating (highest first)")
    print("3. Distance")
    sort_option = ask("Sort by (1-3)", "1")
    
    # 페이지네이션 상태
    page_size = 20
    current_page = 0
    
    while True:
        offset = current_page * page_size
        
        if offset >= total_count:
            print("📋 마지막 페이지입니다.")
            current_page = max(0, current_page - 1)
            continue
        
        # 해당 페이지만 DB에서 로드
        page_results = search_engine.search_by_address_paginated(
            city or "", state, limit=page_size, offset=offset
        )
        
        if not page_results:
            print("더 이상 결과가 없습니다.")
            break
        
        # CMS 정보 및 Google 정보 수집
        _enrich_hospital_data(page_results, 0, len(page_results), page_results,
                             0, search_engine, city, state, user_coords)
        
        # 결과 출력
        print(f"\nShowing {offset+1}-{min(offset+page_size, total_count)} of {total_count} hospitals")
        print("="*70 + "\n")
        
        _display_hospital_results(page_results, offset)
        
        # 메뉴
        print("\n" + "-"*70)
        print("What would you like to do?")
        print("1. 더 보기")
        print("2. 뒤로가기")
        print("3. 나가기")
        print("-"*70)
        
        choice = ask("Select (1-3)", "2")
        
        if choice == "1":
            if offset + page_size >= total_count:
                print("📋 마지막 페이지입니다.")
                continue
            current_page += 1
        elif choice == "2":
            return "back"
        else:
            return "exit"


def _get_user_coordinates(user_city: str, user_state: str):
    """사용자 위치 좌표 가져오기"""
    if not user_city or not user_state:
        return None
    
    try:
        import sys
        from pathlib import Path
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists() or os.getenv("FREE_APIS_OFFLINE") == "1":
            return None
        
        sys.path.insert(0, str(signum_root))
        from free_provider_apis.google.places_client_v1 import PlacesV1Client
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception as e:
                print(f"⚠️ Failed to load .env: {e}")
        
        client = PlacesV1Client(strict=False)
        query = f"{user_city}, {user_state}"
        geo_result = client.search_text(query, fields=["places.location"])
        
        if geo_result.get("places"):
            loc = geo_result["places"][0].get("location")
            if loc:
                coords = (loc.get("latitude"), loc.get("longitude"))
                print(f"✅ Location confirmed: {user_city}, {user_state}")
                return coords
    except Exception as e:
        print(f"⚠️ Could not get location: {e}")
    
    return None


def _enrich_hospital_data(page_results: List, start_idx: int, end_idx: int,
                          all_results: List, google_fetched_up_to: int,
                          search_engine, city: str, state: str, user_coords):
    """병원 데이터에 CMS, Google, Distance, NPI 정보 추가"""
    
    env_lookup = os.getenv("MAX_GOOGLE_LOOKUPS")
    max_google_lookups = int(env_lookup) if env_lookup else 20  # 기본값 20으로 제한
    
    # NPI 검증도 같은 수로 제한
    max_npi_lookups = max_google_lookups
    
    for i, hospital in enumerate(page_results):
        actual_idx = start_idx + i
        
        # CMS 정보가 아직 없으면 조회
        if 'cms_rating' not in hospital:
            info = search_engine.get_cms_rating_with_source(hospital['ccn'])
            rating = info.get('rating')
            hospital['cms_rating'] = rating
            hospital['cms_source'] = info.get('source')
            hospital['cms_confidence'] = info.get('confidence')
            hospital['cms_reason'] = info.get('reason')
            
            # 특수 병원 확인 (CMS 별점이 없는 경우)
            if rating is None:
                # 정신병원 체크
                psych_indicators = search_engine.get_psychiatric_quality_indicators(hospital['ccn'])
                hospital['psychiatric_indicators'] = psych_indicators
                
                # 정신병원이 아니면 소아병원 체크
                if not psych_indicators or not psych_indicators.get('has_data'):
                    pediatric_indicators = search_engine.get_pediatric_quality_indicators(hospital['ccn'])
                    hospital['pediatric_indicators'] = pediatric_indicators
                else:
                    hospital['pediatric_indicators'] = None
            else:
                hospital['psychiatric_indicators'] = None
                hospital['pediatric_indicators'] = None
        
        # NPI 정보가 아직 없으면 조회 (각 페이지마다 수행, 양방향 검증은 생략)
        if 'npi' not in hospital:
            try:
                npi_candidate = get_npi_for_hospital(hospital['facility_name'], hospital.get('state'))
                hospital['npi'] = npi_candidate  # 검증 없이 바로 저장
            except Exception:
                hospital['npi'] = None
        
        # Google 정보가 아직 없고, 아직 조회하지 않은 병원이면
        if 'google_rating' not in hospital and actual_idx >= google_fetched_up_to:
            hospital['google_rating'] = None
            hospital['google_reviews'] = None
            hospital['location'] = None
            
            if os.getenv("FREE_APIS_OFFLINE") != "1" and actual_idx < max_google_lookups:
                try:
                    google_results = try_google_search(f"{hospital['facility_name']} {city or ''} {state}")
                    if google_results:
                        hospital['google_rating'] = google_results[0].get('rating')
                        hospital['google_reviews'] = google_results[0].get('user_rating_count')
                        hospital['location'] = google_results[0].get('location')
                        hospital['google_address'] = google_results[0].get('address')  # 전체 주소 저장
                except Exception:
                    pass
        
        # Distance 계산
        if user_coords and hospital.get('location'):
            hospital_coords = (hospital['location'].get('latitude'),
                             hospital['location'].get('longitude'))
            if hospital_coords[0] and hospital_coords[1]:
                hospital['distance'] = calculate_distance(user_coords, hospital_coords)
            else:
                hospital['distance'] = float('inf')
        else:
            hospital['distance'] = float('inf')


def _display_hospital_results(results: List, start_idx: int):
    """병원 결과 출력"""
    from .risk_analyzer import RiskAnalyzer
    
    # warehouse_dir 찾기
    warehouse_dir = os.path.join(os.path.dirname(__file__), "..", "warehouse")
    risk_analyzer = RiskAnalyzer(warehouse_dir)
    
    for i, hospital in enumerate(results, start_idx + 1):
        print(f"{i}. {hospital['facility_name']}")
        print(f"   CCN: {hospital['ccn']}")
        
        # NPI 표시 (검증된 것만, 아이콘 없이)
        npi = hospital.get('npi')
        if npi:
            print(f"   NPI: {npi}")
        
        # 주소 표시 (Google 주소가 있으면 우선 사용, 없으면 CMS 데이터 사용)
        google_address = hospital.get('google_address')
        if google_address:
            print(f"   Address: {google_address}")
        else:
            # CMS 데이터로 주소 구성 (ZIP 포함)
            zip_code = hospital.get('zip', '')
            if zip_code:
                print(f"   Address: {hospital['city']}, {hospital['state']} {zip_code}")
            else:
                print(f"   Address: {hospital['city']}, {hospital['state']}")
        
        # 특수 병원 (정신병원, 소아병원) 처리
        psych_indicators = hospital.get('psychiatric_indicators')
        pediatric_indicators = hospital.get('pediatric_indicators')
        
        if psych_indicators and psych_indicators.get('has_data'):
            # 정신병원
            print(f"   Hospital Type: 🧠 Psychiatric Facility")
            print(f"   CMS Rating: N/A (Uses specialized quality measures)")
            print(f"   Quality Indicators:")
            for ind in psych_indicators.get('indicators', [])[:3]:
                status = "✓" if ind.get('good') else "•"
                print(f"     {status} {ind['name']}: {ind['value']}")
        elif pediatric_indicators and pediatric_indicators.get('has_data'):
            # 소아병원
            print(f"   Hospital Type: 👶 Pediatric Facility")
            print(f"   CMS Rating: N/A (Uses specialized quality measures)")
            print(f"   Quality Indicators:")
            for ind in pediatric_indicators.get('indicators', [])[:3]:
                status = "✓" if ind.get('good') else "•"
                print(f"     {status} {ind['name']}: {ind['value']}")
        elif psych_indicators and not psych_indicators.get('has_data'):
            print(f"   Hospital Type: 🧠 Psychiatric Facility")
            print(f"   CMS Rating: N/A (Insufficient Data)")
        elif pediatric_indicators and not pediatric_indicators.get('has_data'):
            print(f"   Hospital Type: 👶 Pediatric Facility")
            print(f"   CMS Rating: N/A (Insufficient Data)")
        else:
            # 일반 병원
            cms_rating = hospital.get('cms_rating')
            source = hospital.get('cms_source')
            if cms_rating is not None:
                stars = "⭐" * int(cms_rating)
                if source == 'predicted':
                    conf = hospital.get('cms_confidence')
                    conf_text = f", 신뢰도: {conf:.0%}" if conf is not None else ""
                    tag = f" (AI Predicted{conf_text})"
                elif source == 'estimated':
                    tag = " (Estimated)"
                elif source == 'official':
                    tag = " (Official)"
                else:
                    tag = ""
                print(f"   CMS Rating: {stars} {cms_rating:.1f}/5.0{tag}")
            else:
                reason = hospital.get('cms_reason') or 'N/A'
                print(f"   CMS Rating: N/A ({reason})")
        
        google_rating = hospital.get('google_rating')
        review_count = hospital.get('google_reviews') or 0
        if google_rating is not None and google_rating > 0:
            stars = "⭐" * int(google_rating)
            review_text = f" ({review_count} reviews)" if review_count > 0 else ""
            print(f"   Google Rating: {stars} {google_rating:.1f}/5.0{review_text}")
        else:
            print("   Google Rating: N/A")
        
        # 위험 지표 분석 (캐싱 사용) - 특수 병원 제외
        if not psych_indicators and not pediatric_indicators:
            ccn = hospital['ccn']
            global _risk_cache
            
            if ccn in _risk_cache:
                alerts = _risk_cache[ccn]
            else:
                try:
                    alerts = risk_analyzer.analyze_all_risks(ccn)
                    _risk_cache[ccn] = alerts
                except Exception:
                    alerts = []
            
            if alerts:
                print(f"   ⚠️ 주의 지표:")
                for alert in alerts:
                    msg = alert['message']
                    # 메시지에 이미 국가 평균 정보가 포함되어 있음
                    print(f"      • {msg}")
                print(f"   ℹ️ 참고: 대형 병원은 중증 환자를 더 많이 받아 지표가 높을 수 있습니다.")
        
        # 별점 불일치 분석
        cms_rating = hospital.get('cms_rating')
        if cms_rating and google_rating:
            diff = abs(cms_rating - google_rating)
            
            if diff >= 2.0:
                print(f"   ℹ️ Google과 CMS 별점 차이가 큽니다 ({diff:.1f}점)")
                if review_count < 20:
                    print(f"      Google 리뷰 수가 적어 ({review_count}개) 대표성이 낮을 수 있습니다.")
                else:
                    print(f"      두 지표는 다른 측면을 측정합니다. 함께 참고하세요.")
            elif diff >= 1.0:
                print(f"   ℹ️ Google과 CMS 별점에 다소 차이가 있습니다 ({diff:.1f}점)")
        
        if hospital.get('distance') and hospital['distance'] != float('inf'):
            print(f"   Distance: {hospital['distance']:.1f} miles")
        print()


def calculate_distance(coord1: tuple, coord2: tuple) -> float:
    """Calculate distance between two coordinates in miles (Haversine formula)"""
    import math
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 3959.0
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2)**2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance


def search_by_specialty(warehouse_dir: str) -> str:
    """Search hospitals by specialty using NPPES - returns 'back' or 'exit'"""
    
    print("\nSearch hospitals by specialty:")
    
    specialty = ask("Specialty (e.g., Cardiology)", "")
    state = ask("State (optional)", "")
    city = ask("City (optional)", "")
    
    if not specialty:
        print("❌ Please enter a specialty")
        return show_action_menu()
    
    try:
        import sys
        from pathlib import Path
        
        current_file = Path(__file__).resolve()
        signum_root = current_file.parent.parent.parent
        free_apis_path = signum_root / "free_provider_apis"
        
        if not free_apis_path.exists():
            print("❌ NPPES API not available")
            return show_action_menu()
        
        env_file = free_apis_path / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                import os
                load_dotenv(dotenv_path=str(env_file), override=True)
            except Exception as e:
                print(f"⚠️ Failed to load .env: {e}")
        
        if str(signum_root) not in sys.path:
            sys.path.insert(0, str(signum_root))
        
        from free_provider_apis.government.clients_free import NPPESClient
        
        nppes_client = NPPESClient()
        
        search_params = {
            'taxonomy_description': specialty,
            'enumeration_type': 'NPI-2'
        }
        if state:
            search_params['state'] = state.upper()
        if city:
            search_params['city'] = city
        
        raw_result = nppes_client.search(**search_params, limit=100)  # 더 많이 가져오기
        items = NPPESClient.normalize(raw_result)
        
        if not items:
            print("❌ No results found")
            return show_action_menu()
        
        print(f"\n✅ Found {len(items)} organizations from NPPES")
        
        # NPPES 결과를 저장 (CCN 변환은 페이지별로 수행)
        from .search_engine import HospitalSearchEngine
        search_engine = HospitalSearchEngine(warehouse_dir)
        
        # NPPES 원본 데이터를 저장 (CCN 아직 없음)
        nppes_items = []
        for item in items:
            practice_addr = item.get('practice_addresses', [{}])[0]
            nppes_items.append({
                'npi': item.get('npi'),
                'facility_name': item.get('name', ''),
                'city': practice_addr.get('city'),
                'state': practice_addr.get('state'),
                'zip': practice_addr.get('postal_code'),
                'ccn': None  # 아직 변환 안 됨
            })
        
        # 사용자 위치 입력 (거리 정렬용)
        user_coords = _get_user_coordinates(
            ask("\nEnter your location for distance sorting (optional)\nCity", ""),
            ask("State", "")
        )
        
        # 정렬 옵션
        print("\nSorting options:")
        print("1. CMS rating (highest first)")
        print("2. Google rating (highest first)")
        print("3. Distance")
        sort_option = ask("Sort by (1-3)", "1")
        
        # 페이지네이션
        page_size = 20
        current_page = 0
        google_fetched_up_to = 0
        ccn_resolved_up_to = 0  # CCN 변환된 마지막 인덱스
        
        while True:
            start_idx = current_page * page_size
            end_idx = start_idx + page_size
            
            if start_idx >= len(nppes_items):
                print("📋 마지막 페이지입니다.")
                current_page = max(0, current_page - 1)
                continue
            
            page_results = nppes_items[start_idx:end_idx]
            
            # 페이지별 CCN 변환 (아직 변환 안 된 것만)
            if start_idx >= ccn_resolved_up_to:
                print(f"📊 Resolving CCN for items {start_idx+1}-{min(end_idx, len(nppes_items))}...")
                
                for i, item in enumerate(page_results, 1):
                    if item.get('ccn'):
                        continue  # 이미 변환됨
                    
                    name = item.get('facility_name')
                    
                    # 로컬 DuckDB에서 이름으로 CCN 검색 (빠름)
                    ccn = None
                    if name:
                        try:
                            local_results = search_engine.search_by_name(name, state)
                            if local_results:
                                ccn = local_results[0]['ccn']
                        except Exception:
                            pass
                    
                    item['ccn'] = ccn
                    
                    # 진행 상황 표시 (10개마다)
                    if i % 5 == 0:
                        print(f"  Progress: {i}/{len(page_results)}")
                
                ccn_resolved_up_to = max(ccn_resolved_up_to, end_idx)
            
            # CCN이 있는 병원만 필터링
            valid_results = [h for h in page_results if h.get('ccn')]
            
            if not valid_results:
                print(f"⚠️ No valid hospitals with CCN found in this page")
                current_page += 1
                continue
            
            print(f"✅ Found {len(valid_results)} hospitals with CCN")
            
            # 1번, 3번과 동일: _enrich_hospital_data 사용
            _enrich_hospital_data(
                valid_results, 0, len(valid_results),
                valid_results, google_fetched_up_to,
                search_engine, city or "", state or "", user_coords
            )
            google_fetched_up_to = len(valid_results)
            
            # 정렬
            if sort_option == "1":
                valid_results = sorted(valid_results,
                    key=lambda x: (x.get('cms_rating') is None, -(x.get('cms_rating') or 0)))
            elif sort_option == "2":
                valid_results = sorted(valid_results,
                    key=lambda x: (x.get('google_rating') is None, -(x.get('google_rating') or 0)))
            elif sort_option == "3":
                valid_results = sorted(valid_results,
                    key=lambda x: x.get('distance', float('inf')))
            
            # 결과 출력 (1번, 3번과 동일)
            print(f"\nShowing {start_idx+1}-{min(end_idx, len(nppes_items))} of {len(nppes_items)} organizations")
            print(f"({len(valid_results)} hospitals with CCN)")
            print("="*70 + "\n")
            
            _display_hospital_results(valid_results, 0)
            
            # 메뉴
            print("\n" + "-"*70)
            print("What would you like to do?")
            print("1. 더 보기")
            print("2. 뒤로가기")
            print("3. 나가기")
            print("-"*70)
            
            choice = ask("Select (1-3)", "2")
            
            if choice == "1":
                if end_idx >= len(nppes_items):
                    print("📋 마지막 페이지입니다.")
                    continue
                current_page += 1
            elif choice == "2":
                return "back"
            else:
                return "exit"
    
    except Exception as e:
        print(f"⚠️ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return show_action_menu()