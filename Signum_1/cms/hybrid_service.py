"""
Hybrid Service - Combines Signum_1 historical data with real-time CMS API

This service integrates:
1. Signum_1 DuckDB: Detailed historical metrics (mortality, readmission, etc.)
2. CMS API: Latest star ratings and basic info
3. Provides comprehensive hospital evaluation
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from .unified_service import UnifiedHospitalService


class HybridHospitalService:
    """
    Combines historical detailed data (Signum_1) with real-time CMS API data
    
    Data Sources:
    - Signum_1 DuckDB: Historical metrics, trends, risk analysis
    - CMS PDC API: Latest star ratings, updated information
    """
    
    def __init__(self, warehouse_dir: Optional[str] = None):
        self.service = UnifiedHospitalService(warehouse_dir)
    
    def get_comprehensive_data(self, ccn: str) -> Dict[str, Any]:
        """
        Get comprehensive hospital data combining historical and real-time sources
        
        Args:
            ccn: Hospital CCN
            
        Returns:
            {
                "basic_info": {...},
                "latest_rating": {...},  # From CMS API (real-time)
                "historical_metrics": {...},  # From Signum_1 (detailed)
                "risk_alerts": [...],
                "insights": {...}
            }
        """
        # Get historical detailed data from Signum_1
        historical = self.service.get_hospital_data(ccn)
        
        # Try to get latest rating from API
        # Note: This requires CMS API integration
        latest_rating = None
        try:
            latest_rating = self._get_latest_rating_from_api(ccn)
        except Exception as e:
            # Fallback: use historical data
            latest_rating = {
                "provider_ccn": ccn,
                "hospital_name": historical.get("basic_info", {}).get("facility_name"),
                "overall_rating": historical.get("basic_info", {}).get("current_rating"),
                "source": "historical_fallback"
            }
        
        return {
            "ccn": ccn,
            "basic_info": historical.get("basic_info"),
            "latest_rating": latest_rating,
            "historical_metrics": historical.get("domain_metrics"),
            "risk_alerts": historical.get("risk_alerts", []),
            "insights": historical.get("insights"),
            "history": historical.get("history")
        }
    
    def _get_latest_rating_from_api(self, ccn: str) -> Optional[Dict[str, Any]]:
        """
        Get latest rating from CMS API
        
        Note: This requires CMS PDC client integration
        """
        try:
            import sys
            sys.path.append('../free_provider_apis')
            from government.clients_free import CMSPDCClient
            
            cms_api = CMSPDCClient()
            result = cms_api.get_hospital_quality_by_ccns((ccn,))
            
            if result and ccn in result:
                return result[ccn]
            
            return None
        except ImportError:
            # CMS API not available
            return None
        except Exception:
            return None
    
    def search_and_comprehensive_evaluate(self, query: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Search hospital and provide comprehensive evaluation
        
        Args:
            query: Hospital name or address
            state: State code (optional)
            
        Returns:
            Complete evaluation with historical + real-time data
        """
        # Search using Signum_1
        result = self.service.search_and_evaluate(query, state)
        
        if "error" in result:
            return result
        
        # Get comprehensive data for selected hospital
        ccn = result["selected"]["ccn"]
        comprehensive = self.get_comprehensive_data(ccn)
        
        return {
            "search_results": result["search_results"],
            "selected": result["selected"],
            "comprehensive_evaluation": comprehensive,
            "summary": self._generate_summary(comprehensive)
        }
    
    def _generate_summary(self, data: Dict[str, Any]) -> str:
        """Generate human-readable summary"""
        basic = data.get("basic_info", {})
        insights = data.get("insights", {})
        risk_alerts = data.get("risk_alerts", [])
        latest = data.get("latest_rating", {})
        
        messages = []
        
        # Current rating
        current_rating = latest.get("overall_rating") or basic.get("current_rating")
        if current_rating:
            messages.append(f"Current CMS Quality Rating: {current_rating}/5.0")
        
        # Trend analysis
        if insights:
            trend = insights.get("trend_direction", "Unknown")
            messages.append(f"Growth Trend: {trend}")
        
        # Risk assessment
        high_risks = [r for r in risk_alerts if r.get("severity") == "high"]
        if high_risks:
            messages.append(f"⚠️ High-Risk Indicators: {len(high_risks)} found")
        elif risk_alerts:
            messages.append(f"Caution: Some indicators need attention")
        else:
            messages.append("✅ Risk Assessment: Normal")
        
        return " | ".join(messages)
