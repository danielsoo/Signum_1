"""
SIGNUM API Server - FastAPI Integration
Healthcare Provider Intelligence Platform API

This API provides endpoints for:
- Hospital search and analytics
- Provider lookup (NPPES integration)
- Risk analysis and predictions
- Multi-source data integration (Google Places, CMS, NPPES)
"""

from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi import Limiter, _rate_limit_exceeded_handler
import logging
import asyncio
from pathlib import Path
import sys
import os
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

# Add the provider module to Python path
current_dir = Path(__file__).resolve().parent
provider_path = current_dir / "provider"
if str(provider_path) not in sys.path:
    sys.path.insert(0, str(provider_path))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
# Key function: identifies users by IP address
# Storage: in-memory (for single instance) or Redis for distributed systems
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="SIGNUM Healthcare Provider Intelligence API",
    description="Comprehensive healthcare provider search and analytics platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = provider_path / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
except ImportError:
    logger.warning("python-dotenv not available, skipping .env loading")

# Global service instances
_unified_service = None
_hospital_search = None
_risk_analyzer = None
_nppes_client = None
_cms_client = None
_google_client = None

# Import classes
UnifiedHospitalService = None
HospitalSearchEngine = None
RiskAnalyzer = None
NPPESClient = None
CMSPDCClient = None
PlacesV1Client = None


def initialize_services():
    """Initialize all SIGNUM services"""
    global UnifiedHospitalService, HospitalSearchEngine, RiskAnalyzer
    global NPPESClient, CMSPDCClient, PlacesV1Client
    global _unified_service, _hospital_search, _risk_analyzer, _nppes_client, _google_client

    logger.info("🔧 Initializing SIGNUM services...")

    # Import hospital modules
    try:
        from provider.hospital import UnifiedHospitalService as UHS
        from provider.hospital import HospitalSearchEngine as HSE
        from provider.hospital import RiskAnalyzer as RA
        UnifiedHospitalService = UHS
        HospitalSearchEngine = HSE
        RiskAnalyzer = RA
        logger.info("✅ Hospital modules imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import hospital modules: {e}")

    # Import government modules
    try:
        from provider.government.clients_free import NPPESClient as NPC
        NPPESClient = NPC
        logger.info("✅ NPPES client imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import NPPES client: {e}")

    # Import Google modules
    try:
        from provider.google.places_client_v1 import PlacesV1Client as PVC
        PlacesV1Client = PVC
        logger.info("✅ Google Places client imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import Google Places client: {e}")

    # Initialize instances
    if UnifiedHospitalService:
        try:
            _unified_service = UnifiedHospitalService()
            logger.info("✅ Unified service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize unified service: {e}")

    if HospitalSearchEngine:
        try:
            warehouse_dir = provider_path / "hospital" / "warehouse"
            warehouse_dir.mkdir(parents=True, exist_ok=True)
            _hospital_search = HospitalSearchEngine(str(warehouse_dir))
            logger.info("✅ Hospital search engine initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize hospital search: {e}")

    if RiskAnalyzer:
        try:
            _risk_analyzer = RiskAnalyzer()
            logger.info("✅ Risk analyzer initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize risk analyzer: {e}")

    if NPPESClient:
        try:
            _nppes_client = NPPESClient()
            logger.info("✅ NPPES client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NPPES client: {e}")

    if PlacesV1Client:
        try:
            _google_client = PlacesV1Client(strict=False)
            logger.info("✅ Google Places client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google client: {e}")


def get_unified_service():
    """Get or create unified hospital service instance"""
    return _unified_service


def get_hospital_search():
    """Get or create hospital search engine instance"""
    return _hospital_search


def get_risk_analyzer():
    """Get or create risk analyzer instance"""
    return _risk_analyzer


def get_nppes_client():
    """Get or create NPPES client instance"""
    return _nppes_client


def get_google_client():
    """Get or create Google Places client instance"""
    return _google_client


# Global service instances
_unified_service = None
_hospital_search = None
_risk_analyzer = None
_nppes_client = None
_cms_client = None
_google_client = None


def get_unified_service():
    """Get or create unified hospital service instance"""
    global _unified_service
    if _unified_service is None and UnifiedHospitalService:
        try:
            _unified_service = UnifiedHospitalService()
            logger.info("Unified hospital service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize unified service: {e}")
    return _unified_service


def get_hospital_search():
    """Get or create hospital search engine instance"""
    global _hospital_search
    if _hospital_search is None and HospitalSearchEngine:
        try:
            _hospital_search = HospitalSearchEngine()
            logger.info("Hospital search engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize hospital search: {e}")
    return _hospital_search


def get_risk_analyzer():
    """Get or create risk analyzer instance"""
    global _risk_analyzer
    if _risk_analyzer is None and RiskAnalyzer:
        try:
            _risk_analyzer = RiskAnalyzer()
            logger.info("Risk analyzer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize risk analyzer: {e}")
    return _risk_analyzer


def get_nppes_client():
    """Get or create NPPES client instance"""
    global _nppes_client
    if _nppes_client is None and NPPESClient:
        try:
            _nppes_client = NPPESClient()
            logger.info("NPPES client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize NPPES client: {e}")
    return _nppes_client


def get_google_client():
    """Get or create Google Places client instance"""
    global _google_client
    if _google_client is None and PlacesV1Client:
        try:
            _google_client = PlacesV1Client(strict=False)
            logger.info("Google Places client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google client: {e}")
    return _google_client

# Pydantic models for request/response validation


class ProviderSearchRequest(BaseModel):
    """Provider search request model"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: Optional[str] = None
    specialty: Optional[str] = Field(
        None, description="Medical specialty or taxonomy description")
    city: Optional[str] = None
    state: Optional[str] = Field(
        None, max_length=2, description="2-letter state code")
    postal_code: Optional[str] = None
    limit: int = Field(
        10, ge=1, le=100, description="Maximum number of results")


class HospitalSearchRequest(BaseModel):
    """Hospital search request model"""
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    ccn: Optional[str] = Field(
        None, description="6-digit CMS Certification Number")
    include_predictions: bool = Field(
        True, description="Include AI predictions")
    include_risk_analysis: bool = Field(
        True, description="Include risk analysis")


class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

# Startup event to initialize services


@app.on_event("startup")
async def startup_event():
    """Initialize SIGNUM services on startup"""
    logger.info("🚀 Starting SIGNUM API Server...")
    initialize_services()
    logger.info("✅ Startup complete")

# Health check endpoint


@app.get("/health", response_model=Dict[str, Any])
@limiter.limit("60/minute")  # Allow 60 health checks per minute
async def health_check(request: Request):
    """Health check endpoint with service status"""
    services_status = {
        "unified_service": get_unified_service() is not None,
        "hospital_search": get_hospital_search() is not None,
        "risk_analyzer": get_risk_analyzer() is not None,
        "nppes_client": get_nppes_client() is not None,
        "google_client": get_google_client() is not None,
    }

    return {
        "status": "healthy",
        "services": services_status,
        "environment": {
            "google_api_configured": bool(os.getenv("GOOGLE_API_KEY")),
            "offline_mode": os.getenv("FREE_APIS_OFFLINE", "0") == "1"
        }
    }

# Provider search endpoints


@app.get("/api/v1/providers/search", response_model=APIResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def search_providers(
    request: Request,
    first_name: Optional[str] = Query(None),
    last_name: Optional[str] = Query(None),
    organization_name: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None, description="Medical specialty"),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None, max_length=2),
    postal_code: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Search healthcare providers using NPPES database

    Search by provider name, organization, specialty, or location.
    Returns normalized provider data with practice locations and taxonomies.
    """
    try:
        nppes_client = get_nppes_client()
        if not nppes_client:
            raise HTTPException(
                status_code=503, detail="NPPES service unavailable")

        # Perform NPPES search
        results = nppes_client.search(
            first_name=first_name,
            last_name=last_name,
            organization_name=organization_name,
            taxonomy_description=specialty,
            city=city,
            state=state.upper() if state else None,
            postal_code=postal_code,
            limit=limit
        )

        # Normalize results
        normalized_results = nppes_client.normalize(results)

        return APIResponse(
            success=True,
            data={"providers": normalized_results},
            count=len(normalized_results),
            metadata={
                "source": "NPPES",
                "search_params": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "organization_name": organization_name,
                    "specialty": specialty,
                    "city": city,
                    "state": state,
                    "postal_code": postal_code
                }
            }
        )

    except Exception as e:
        logger.error(f"Provider search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/providers/{npi}", response_model=APIResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def get_provider_by_npi(npi: str, request: Request):
    """
    Get detailed provider information by NPI number

    Returns comprehensive provider data including practice locations,
    taxonomies, and identifiers.
    """
    try:
        if len(npi) != 10 or not npi.isdigit():
            raise HTTPException(
                status_code=400, detail="NPI must be 10 digits")

        nppes_client = get_nppes_client()
        if not nppes_client:
            raise HTTPException(
                status_code=503, detail="NPPES service unavailable")

        # Search by NPI
        results = nppes_client.search(number=npi, limit=1)
        normalized_results = nppes_client.normalize(results)

        if not normalized_results:
            raise HTTPException(status_code=404, detail="Provider not found")

        provider = normalized_results[0]

        return APIResponse(
            success=True,
            data={"provider": provider},
            metadata={"source": "NPPES", "npi": npi}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Provider lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Hospital search endpoints


@app.get("/api/v1/hospitals/search", response_model=APIResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def search_hospitals(
    request: Request,
    name: Optional[str] = Query(None, description="Hospital name"),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    ccn: Optional[str] = Query(
        None, description="6-digit CMS Certification Number"),
    include_predictions: bool = Query(True),
    include_risk_analysis: bool = Query(True),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Search hospitals in CMS database

    Search by hospital name, location, or CCN. Optionally includes
    AI predictions and risk analysis.
    """
    try:
        hospital_search = get_hospital_search()
        if not hospital_search:
            raise HTTPException(
                status_code=503, detail="Hospital search service unavailable")

        results = []

        if ccn:
            # Search by CCN
            hospital = hospital_search.get_by_ccn(ccn)
            if hospital:
                results = [hospital]
        elif name:
            # Search by name
            search_results = hospital_search.search_by_name(name, state=state)
            # Apply limit if specified
            if limit and search_results:
                search_results = search_results[:limit]
            results = search_results if search_results else []
        elif city or state:
            # Search by location
            location_results = hospital_search.search_by_address(
                city=city or "", state=state
            )
            # Apply limit if specified
            if limit and location_results:
                location_results = location_results[:limit]
            results = location_results if location_results else []
        else:
            raise HTTPException(
                status_code=400, detail="At least one search parameter required")

        # Enhance results with additional data
        enhanced_results = []
        for hospital in results:
            enhanced_hospital = hospital.copy()

            if include_predictions and hospital.get("ccn"):
                try:
                    # Get latest star rating
                    rating = hospital_search.get_latest_star_rating(
                        hospital["ccn"])
                    if rating:
                        enhanced_hospital["current_rating"] = rating
                except Exception as e:
                    logger.warning(
                        f"Failed to get rating for CCN {hospital.get('ccn')}: {e}")

            if include_risk_analysis and hospital.get("ccn"):
                try:
                    risk_analyzer = get_risk_analyzer()
                    if risk_analyzer:
                        alerts = risk_analyzer.analyze_all_risks(
                            hospital["ccn"])
                        enhanced_hospital["risk_alerts"] = alerts
                except Exception as e:
                    logger.warning(
                        f"Failed to get risk analysis for CCN {hospital.get('ccn')}: {e}")

            enhanced_results.append(enhanced_hospital)

        return APIResponse(
            success=True,
            data={"hospitals": enhanced_results},
            count=len(enhanced_results),
            metadata={
                "source": "CMS",
                "search_params": {
                    "name": name,
                    "city": city,
                    "state": state,
                    "ccn": ccn
                },
                "features": {
                    "predictions_included": include_predictions,
                    "risk_analysis_included": include_risk_analysis
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hospital search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/hospitals/{ccn}/comprehensive", response_model=APIResponse)
@limiter.limit("20/minute")  # 20 requests per minute per IP (data-intensive)
async def get_hospital_comprehensive(ccn: str, request: Request):
    """
    Get comprehensive hospital analysis including all available data

    Returns hospital basic info, historical data, risk analysis,
    predictions, and insights using the unified service.
    """
    try:
        if len(ccn) != 6 or not ccn.isdigit():
            raise HTTPException(status_code=400, detail="CCN must be 6 digits")

        unified_service = get_unified_service()
        if not unified_service:
            raise HTTPException(
                status_code=503, detail="Unified service unavailable")

        # Get comprehensive hospital data
        hospital_data = unified_service.get_hospital_data(ccn)

        if not hospital_data or not hospital_data.get("basic_info"):
            raise HTTPException(status_code=404, detail="Hospital not found")

        return APIResponse(
            success=True,
            data={"hospital": hospital_data},
            metadata={
                "source": "SIGNUM_Unified",
                "ccn": ccn,
                "features": [
                    "basic_info",
                    "star_rating_history",
                    "risk_analysis",
                    "quality_insights",
                    "ai_predictions"
                ]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comprehensive hospital data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Risk analysis endpoint


@app.get("/api/v1/hospitals/{ccn}/risk-analysis", response_model=APIResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def get_hospital_risk_analysis(ccn: str, request: Request):
    """
    Get detailed risk analysis for a hospital

    Returns comprehensive risk alerts across multiple domains
    including mortality, safety, readmission, and experience.
    """
    try:
        if len(ccn) != 6 or not ccn.isdigit():
            raise HTTPException(status_code=400, detail="CCN must be 6 digits")

        risk_analyzer = get_risk_analyzer()
        if not risk_analyzer:
            raise HTTPException(
                status_code=503, detail="Risk analyzer unavailable")

        # Get all risk alerts
        alerts = risk_analyzer.analyze_all_risks(ccn)

        # Categorize alerts by severity
        risk_summary = {
            "high_risk": [a for a in alerts if a.get("severity") == "HIGH"],
            "medium_risk": [a for a in alerts if a.get("severity") == "MEDIUM"],
            "low_risk": [a for a in alerts if a.get("severity") == "LOW"],
            "total_alerts": len(alerts)
        }

        return APIResponse(
            success=True,
            data={
                "ccn": ccn,
                "alerts": alerts,
                "summary": risk_summary
            },
            count=len(alerts),
            metadata={
                "source": "SIGNUM_RiskAnalyzer",
                "analysis_domains": [
                    "mortality",
                    "safety",
                    "readmission",
                    "experience",
                    "effectiveness"
                ]
            }
        )

    except Exception as e:
        logger.error(f"Risk analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced search with Google Places integration


@app.get("/api/v1/hospitals/enhanced-search", response_model=APIResponse)
# 20 requests per minute per IP (calls external Google API)
@limiter.limit("20/minute")
async def enhanced_hospital_search(
    request: Request,
    query: str = Query(...,
                       description="Search query (hospital name, location, etc.)"),
    include_google_data: bool = Query(
        True, description="Include Google Places data"),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Enhanced hospital search with Google Places integration

    Combines CMS hospital data with Google Places ratings,
    reviews, and location data for comprehensive results.
    """
    try:
        results = []

        # First search in CMS database
        hospital_search = get_hospital_search()
        if hospital_search:
            cms_results = hospital_search.search_by_name(query)
            # Apply limit if specified
            if limit and cms_results:
                cms_results = cms_results[:limit]
            if cms_results:
                results.extend(cms_results)

        # Enhance with Google Places data if requested
        if include_google_data and results:
            google_client = get_google_client()
            if google_client:
                for hospital in results:
                    try:
                        # Search Google Places for this hospital
                        hospital_name = hospital.get("facility_name", "")
                        if hospital_name:
                            google_results = google_client.text_search(
                                query=f"{hospital_name} hospital",
                                timeout=10
                            )

                            if google_results.get("places"):
                                # Take the first matching place
                                place = google_results["places"][0]
                                hospital["google_data"] = {
                                    "place_id": place.get("id"),
                                    "rating": place.get("rating"),
                                    "user_rating_count": place.get("userRatingCount"),
                                    "formatted_address": place.get("formattedAddress"),
                                    "phone": place.get("nationalPhoneNumber"),
                                    "website": place.get("websiteUri")
                                }
                    except Exception as e:
                        logger.warning(
                            f"Failed to get Google data for hospital {hospital.get('facility_name')}: {e}")

        return APIResponse(
            success=True,
            data={"hospitals": results},
            count=len(results),
            metadata={
                "source": "CMS + Google_Places" if include_google_data else "CMS",
                "query": query,
                "google_enhanced": include_google_data and any(h.get("google_data") for h in results)
            }
        )

    except Exception as e:
        logger.error(f"Enhanced search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System status and analytics endpoint


@app.get("/api/v1/system/status", response_model=APIResponse)
@limiter.limit("60/minute")  # 60 requests per minute per IP
async def get_system_status(request: Request):
    """
    Get comprehensive system status and analytics

    Returns database status, available data ranges, service health,
    and system capabilities.
    """
    try:
        status_data = {}

        # Check hospital search engine status
        hospital_search = get_hospital_search()
        if hospital_search:
            try:
                # Get database connection info
                db_status = hospital_search.get_connection_status()
                status_data["database"] = db_status
            except Exception as e:
                status_data["database"] = {"error": str(e)}

        # Check service availability
        status_data["services"] = {
            "unified_service": get_unified_service() is not None,
            "hospital_search": get_hospital_search() is not None,
            "risk_analyzer": get_risk_analyzer() is not None,
            "nppes_client": get_nppes_client() is not None,
            "google_client": get_google_client() is not None,
        }

        # Environment info
        status_data["environment"] = {
            "google_api_configured": bool(os.getenv("GOOGLE_API_KEY")),
            "offline_mode": os.getenv("FREE_APIS_OFFLINE", "0") == "1",
            "warehouse_dir": os.getenv("CMS_WAREHOUSE_DIR", "provider/hospital/warehouse"),
            "reports_dir": os.getenv("CMS_REPORTS_DIR", "provider/hospital/reports")
        }

        return APIResponse(
            success=True,
            data=status_data,
            # Add real timestamp
            metadata={"timestamp": "2024-01-01T00:00:00Z"}
        )

    except Exception as e:
        logger.error(f"System status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))

    print(f"""
🏥 SIGNUM Healthcare Provider Intelligence API
===============================================
📊 Interactive API docs: http://localhost:{port}/docs
📖 ReDoc documentation: http://localhost:{port}/redoc
🔍 Health check: http://localhost:{port}/health

Available endpoints:
- GET /api/v1/providers/search - Search healthcare providers
- GET /api/v1/providers/{{npi}} - Get provider by NPI
- GET /api/v1/hospitals/search - Search hospitals  
- GET /api/v1/hospitals/{{ccn}}/comprehensive - Comprehensive hospital data
- GET /api/v1/hospitals/{{ccn}}/risk-analysis - Risk analysis
- GET /api/v1/hospitals/enhanced-search - Enhanced search with Google data
- GET /api/v1/system/status - System status

Starting server on port {port}...
""")

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
