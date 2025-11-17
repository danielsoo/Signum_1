"""
Unified Service - 전체 통합 서비스
Google + NPPES + CMS 데이터 통합 제공
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from .search_engine import HospitalSearchEngine
from .risk_analyzer import RiskAnalyzer
from .rating_comparator import RatingComparator
from .insights import InsightsAnalyzer


class UnifiedHospitalService:
    """병원 검색 및 통합 평가 서비스"""
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        self.search_engine = HospitalSearchEngine(warehouse_dir)
        self.risk_analyzer = RiskAnalyzer(warehouse_dir)
        self.rating_comparator = RatingComparator()
        self.insights_analyzer = InsightsAnalyzer(warehouse_dir)
    
    def get_hospital_data(self, ccn: str, google_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        병원의 모든 CMS 데이터 통합 조회
        
        Args:
            ccn: 병원 CCN
            google_data: Google Places 데이터 (선택)
        
        Returns:
            {
                "basic": {...},
                "history": {...},
                "insights": {...},
                "risk_alerts": [...],
                "rating_comparison": {...}
            }
        """
        result = {
            "ccn": ccn
        }
        
        # 1. 기본 정보
        hospital_info = self.search_engine.get_by_ccn(ccn)
        if hospital_info:
            result["basic_info"] = hospital_info
            result["basic_info"]["current_rating"] = self.search_engine.get_latest_star_rating(ccn)
        
        # 2. 히스토리 (최근 별점 변화)
        history = self._get_star_history(ccn)
        result["history"] = history
        
        # 3. 성장 추세 분석
        try:
            insights = self.insights_analyzer.calculate_growth_index(ccn, history.get("latest_release", ""))
            result["insights"] = insights
        except Exception:
            result["insights"] = None
        
        # 4. 도메인별 메트릭
        domain_metrics = self.risk_analyzer.get_domain_metrics(ccn)
        result["domain_metrics"] = domain_metrics
        
        # 5. 위험 경고
        risk_alerts = self.risk_analyzer.analyze_all_risks(ccn)
        result["risk_alerts"] = risk_alerts
        
        # 6. Google vs CMS 별점 비교
        if google_data and "rating" in google_data:
            google_rating = google_data.get("rating")
            cms_rating = result["basic_info"].get("current_rating")
            rating_comp = self.rating_comparator.compare_ratings(google_rating, cms_rating)
            result["rating_comparison"] = rating_comp
        
        return result
    
    def _get_star_history(self, ccn: str, limit: int = 12) -> Dict[str, Any]:
        """별점 히스토리 조회"""
        import os
        import duckdb
        
        db_path = os.path.join(self.search_engine.warehouse_dir, "hospital.duckdb")
        if not os.path.exists(db_path):
            return {}
        
        con = duckdb.connect(db_path, read_only=True)
        try:
            query = """
                SELECT release, star_rating
                FROM hospital_star 
                WHERE ccn = ? AND star_rating IS NOT NULL
                ORDER BY release DESC
                LIMIT ?
            """
            df = con.execute(query, [ccn, limit]).df()
            
            ratings = []
            for _, row in df.iterrows():
                ratings.append({
                    "release": str(row['release']),
                    "rating": float(row['star_rating'])
                })
            
            return {
                "latest_release": ratings[0]['release'] if ratings else None,
                "recent_ratings": ratings
            }
            
        finally:
            con.close()
    
    def search_and_evaluate(self, query: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        병원 검색 및 평가
        
        Args:
            query: 병원명 또는 주소
            state: 주 코드 (선택)
        
        Returns:
            {
                "search_results": [...],
                "selected": {...},
                "evaluation": {...}
            }
        """
        # 1. 검색
        results = self.search_engine.search_by_name(query, state)
        
        if not results:
            return {
                "error": "검색 결과 없음",
                "suggestion": "다른 검색어로 시도해주세요"
            }
        
        # 2. 첫 번째 결과 선택
        selected = results[0]
        ccn = selected['ccn']
        
        # 3. 평가
        evaluation = self.get_hospital_data(ccn)
        
        return {
            "search_results": results[:5],  # 상위 5개만
            "selected": selected,
            "evaluation": evaluation
        }
    
    def get_summary(self, ccn: str, google_data: Optional[Dict] = None) -> str:
        """
        인사이트 텍스트 요약 생성
        
        Returns:
            "평가 메시지"
        """
        data = self.get_hospital_data(ccn, google_data)
        
        messages = []
        
        # 기본 정보
        basic = data.get("basic_info", {})
        current_rating = basic.get("current_rating")
        if current_rating:
            messages.append(f"현재 CMS 의료 품질: {current_rating}/5.0")
        
        # 성장 추세
        insights = data.get("insights")
        if insights:
            trend = insights.get("trend_direction")
            if trend == "Improving":
                messages.append("성장 추세: 개선 중")
            elif trend == "Declining":
                messages.append("성장 추세: 하락 중")
            else:
                messages.append("성장 추세: 안정적")
        
        # 위험 경고
        risk_alerts = data.get("risk_alerts", [])
        high_risks = [r for r in risk_alerts if r.get("severity") == "high"]
        if high_risks:
            messages.append(f"⚠️ 고위험 지표: {len(high_risks)}개 발견")
        elif risk_alerts:
            messages.append("주의 사항 일부 존재")
        else:
            messages.append("✅ 위험 지표 정상")
        
        # 별점 비교
        rating_comp = data.get("rating_comparison")
        if rating_comp:
            consistency = rating_comp.get("consistency")
            if consistency == "high":
                messages.append("Google과 CMS 평점 일관성 높음")
        
        return " | ".join(messages)
