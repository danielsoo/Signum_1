"""
사용 예시: Unified Service 연동

이 파일은 예시입니다. 
실제 사용할 때는 Google, NPPES API 클라이언트와 함께 사용하세요.
"""

from unified_service import UnifiedHospitalService


def example_basic_search():
    """기본 병원 검색 예시"""
    service = UnifiedHospitalService()
    
    # 1. 병원명으로 검색 및 평가
    result = service.search_and_evaluate("Mayo Clinic")
    
    print("검색 결과:", result["search_results"])
    print("선택된 병원:", result["selected"])
    print("평가 결과:", result["evaluation"])


def example_with_google_data():
    """Google 데이터와 함께 사용 예시"""
    service = UnifiedHospitalService()
    
    # 2. Google 검색 결과
    google_data = {
        "rating": 4.8,
        "user_rating_count": 8543,
        "photos": ["url1", "url2"],
        "address": "200 1st St SW, Rochester, MN"
    }
    
    # 3. CCN으로 CMS 데이터 조회 (Google 데이터 포함)
    ccn = "390048"
    evaluation = service.get_hospital_data(ccn, google_data)
    
    print("기본 정보:", evaluation["basic_info"])
    print("성장 추세:", evaluation["insights"])
    print("위험 경고:", evaluation["risk_alerts"])
    print("별점 비교:", evaluation["rating_comparison"])
    
    # 4. 요약 메시지
    summary = service.get_summary(ccn, google_data)
    print("요약:", summary)


def example_doctor_search():
    """의사 검색 → 소속 병원 평가 (통합 예시)"""
    
    # 의사 검색은 NPPES에서 처리
    # NPPES에서 NPI 찾고 → 소속 병원 CCN 목록 받기
    
    from free_provider_apis.government.clients_free import NPPESClient, CMSPDCClient
    
    # 1. NPPES에서 의사 검색
    nppes_client = NPPESClient()
    result = nppes_client.search(
        first_name="John",
        last_name="Smith",
        limit=1
    )
    
    if not result.get("results"):
        print("의사를 찾을 수 없습니다")
        return
    
    npi = result["results"][0]["number"]
    
    # 2. 소속 병원 CCN 목록 가져오기
    cms_pdc = CMSPDCClient()
    affiliations = cms_pdc.get_hospital_affiliations_by_npi(npi)
    
    ccns = [a["ccn"] for a in affiliations if a.get("ccn")]
    
    # 3. 각 병원 평가
    service = UnifiedHospitalService()
    
    for ccn in ccns:
        evaluation = service.get_hospital_data(ccn)
        summary = service.get_summary(ccn)
        
        print(f"\n병원 CCN: {ccn}")
        print(f"요약: {summary}")


if __name__ == "__main__":
    print("=== 기본 검색 예시 ===")
    example_basic_search()
    
    print("\n=== Google 데이터와 함께 사용 ===")
    example_with_google_data()
    
    print("\n=== 의사 검색 → 병원 평가 ===")
    example_doctor_search()
