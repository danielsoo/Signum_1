"""
Rating Comparator - Google vs CMS 별점 비교 분석
"""
from __future__ import annotations
from typing import Dict, Optional, Any


class RatingComparator:
    """Google 별점과 CMS 별점 비교 분석"""
    
    @staticmethod
    def compare_ratings(google_rating: Optional[float], cms_rating: Optional[float]) -> Dict[str, Any]:
        """
        Google vs CMS 별점 비교
        
        Args:
            google_rating: Google 별점 (0-5)
            cms_rating: CMS 의료 품질 별점 (1-5)
        
        Returns:
            {
                "google_rating": 4.8,
                "cms_rating": 4.5,
                "difference": 0.3,
                "consistency": "high|medium|low",
                "analysis": "...",
                "confidence": 0.93
            }
        """
        if google_rating is None or cms_rating is None:
            return {
                "google_rating": google_rating,
                "cms_rating": cms_rating,
                "difference": None,
                "consistency": "unknown",
                "analysis": "별점 비교 데이터 불완전",
                "confidence": None
            }
        
        # 차이 계산
        diff = abs(google_rating - cms_rating)
        
        # 일관성 판단
        if diff < 1.0:
            consistency = "high"
            confidence = 1.0 - (diff * 0.3)  # 차이가 작을수록 높은 신뢰도
            analysis = "일관성 높은 결과 관찰됨"
        elif diff < 2.0:
            consistency = "medium"
            confidence = 0.7 - ((diff - 1.0) * 0.4)
            analysis = "일관성 중간 - 추가 확인 권장"
        else:
            consistency = "low"
            confidence = 0.3
            analysis = "일관성 낮음 - 신중한 검토 필요"
        
        return {
            "google_rating": google_rating,
            "cms_rating": cms_rating,
            "difference": diff,
            "consistency": consistency,
            "analysis": analysis,
            "confidence": confidence
        }
    
    @staticmethod
    def analyze_pattern(google_rating: Optional[float], cms_rating: Optional[float]) -> str:
        """
        별점 패턴 분석
        
        Returns:
            "일관성 높음" or "불일치 패턴 관찰" or "신중 검토 필요"
        """
        if google_rating is None or cms_rating is None:
            return "비교 데이터 부족"
        
        diff = google_rating - cms_rating
        
        if abs(diff) < 0.5:
            return "일관성 높음"
        elif diff > 1.0:
            return "Google 평점이 높게 나타나며 마케팅/인지도 효과 가능성"
        elif diff < -1.0:
            return "CMS 의료 품질이 더 높게 나타나며 의료 수준이 더 우수할 가능성"
        else:
            return "안정적인 패턴 관찰"
    
    @staticmethod
    def get_recommendation(google_rating: Optional[float], cms_rating: Optional[float]) -> str:
        """추천 메시지 생성"""
        if google_rating is None or cms_rating is None:
            return "평가 제한적"
        
        diff = google_rating - cms_rating
        
        if diff < -0.5:
            # CMS가 더 높음
            return "의료 품질이 서비스 수준보다 높을 가능성"
        elif diff > 0.5:
            # Google이 더 높음
            return "일반 평가가 높으나 의료 성과는 다를 수 있음"
        else:
            return "다각도에서 긍정적인 평가 가능"
