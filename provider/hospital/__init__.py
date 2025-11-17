"""
CMS Hospital Analytics System

Provides:
- Hospital search engine
- Risk analysis
- Rating comparison
- Unified evaluation service
"""

__version__ = "0.2.0"

# New unified service
from .unified_service import UnifiedHospitalService
from .search_engine import HospitalSearchEngine
from .risk_analyzer import RiskAnalyzer
from .rating_comparator import RatingComparator

__all__ = [
    "UnifiedHospitalService",
    "HospitalSearchEngine", 
    "RiskAnalyzer",
    "RatingComparator",
]