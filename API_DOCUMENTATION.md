# 🏥 SIGNUM API Documentation

**Healthcare Provider Intelligence Platform REST API**

## 🚀 Quick Start

### 1. Setup and Installation

```bash
# Clone or navigate to your SIGNUM directory
cd /Users/harshmaheshwari/development/Signum_1

# Run the startup script (it will handle everything)
./start_api.sh
```

The startup script will:
- Create a virtual environment
- Install all required dependencies
- Create configuration files
- Set up directory structure
- Start the API server

### 2. Access the API

- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc  
- **Health Check**: http://localhost:8000/health

## 📋 API Endpoints Overview

### Health & System Status

#### `GET /health`
Basic health check with service status
```json
{
  "status": "healthy",
  "services": {
    "unified_service": true,
    "hospital_search": true,
    "risk_analyzer": true,
    "nppes_client": true,
    "google_client": false
  },
  "environment": {
    "google_api_configured": false,
    "offline_mode": false
  }
}
```

#### `GET /api/v1/system/status`
Comprehensive system status and analytics

### Provider Search (NPPES Integration)

#### `GET /api/v1/providers/search`
Search healthcare providers using government NPPES database

**Parameters:**
- `first_name` (optional): Provider first name
- `last_name` (optional): Provider last name  
- `organization_name` (optional): Organization name
- `specialty` (optional): Medical specialty (e.g., "Cardiology")
- `city` (optional): City name
- `state` (optional): 2-letter state code
- `postal_code` (optional): ZIP code
- `limit` (optional): Max results (1-100, default: 10)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/providers/search?specialty=Cardiology&state=PA&limit=5"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "providers": [
      {
        "npi": "1234567890",
        "name": "Dr. John Smith",
        "enumeration_type": "NPI-1",
        "status": "A",
        "taxonomies": [
          {
            "code": "207RC0000X",
            "desc": "Cardiovascular Disease",
            "primary": true
          }
        ],
        "practice_addresses": [
          {
            "address_1": "123 Main St",
            "city": "Philadelphia", 
            "state": "PA",
            "postal_code": "19103",
            "telephone_number": "215-555-0123"
          }
        ]
      }
    ]
  },
  "count": 1,
  "metadata": {
    "source": "NPPES",
    "search_params": {...}
  }
}
```

#### `GET /api/v1/providers/{npi}`
Get detailed provider information by NPI number

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/providers/1234567890"
```

### Hospital Search (CMS Integration)

#### `GET /api/v1/hospitals/search`
Search hospitals in CMS database

**Parameters:**
- `name` (optional): Hospital name
- `city` (optional): City name
- `state` (optional): State name
- `ccn` (optional): 6-digit CMS Certification Number
- `include_predictions` (optional): Include AI predictions (default: true)
- `include_risk_analysis` (optional): Include risk analysis (default: true)
- `limit` (optional): Max results (1-50, default: 10)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/hospitals/search?name=Mayo&include_predictions=true"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "hospitals": [
      {
        "ccn": "240001",
        "facility_name": "Mayo Clinic Hospital",
        "city": "Rochester",
        "state": "MN",
        "current_rating": {
          "overall_rating": 5,
          "mortality_rating": "Above",
          "safety_rating": "Above",
          "readmission_rating": "Same"
        },
        "risk_alerts": [
          {
            "severity": "LOW",
            "domain": "Mortality", 
            "message": "Stable mortality trends"
          }
        ]
      }
    ]
  },
  "count": 1
}
```

#### `GET /api/v1/hospitals/{ccn}/comprehensive`
Get comprehensive hospital analysis with all available data

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/hospitals/240001/comprehensive"
```

### Risk Analysis

#### `GET /api/v1/hospitals/{ccn}/risk-analysis`
Get detailed risk analysis for a hospital

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/hospitals/240001/risk-analysis"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "ccn": "240001",
    "alerts": [
      {
        "severity": "HIGH",
        "domain": "Safety",
        "measure": "PSI_03_PRESSURE_ULCER_RATE",
        "message": "Safety score significantly below national average",
        "current_value": 0.45,
        "national_average": 0.28
      }
    ],
    "summary": {
      "high_risk": 1,
      "medium_risk": 2, 
      "low_risk": 3,
      "total_alerts": 6
    }
  }
}
```

### Enhanced Search (Google Places Integration)

#### `GET /api/v1/hospitals/enhanced-search`
Enhanced hospital search with Google Places integration

**Parameters:**
- `query` (required): Search query (hospital name, location, etc.)
- `include_google_data` (optional): Include Google Places data (default: true)
- `limit` (optional): Max results (1-20, default: 5)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/hospitals/enhanced-search?query=Mayo%20Clinic&include_google_data=true"
```

## 🔧 Configuration

### Environment Variables

Create `provider/.env` file:

```bash
# Google Places API (optional)
GOOGLE_API_KEY=your_google_api_key_here

# Feature flags
FREE_APIS_OFFLINE=0  # Set to 1 to disable external APIs

# API server settings  
PORT=8000
HOST=0.0.0.0

# Data directories
CMS_WAREHOUSE_DIR=provider/hospital/warehouse
CMS_REPORTS_DIR=provider/hospital/reports

# AI features
DISABLE_AI=0  # Set to 1 to disable AI features
```

### Data Setup

1. **Hospital Data**: Place CMS hospital ZIP files in `provider/hospital/data/`
2. **First-time Training**: Run the hospital learning pipeline:
   ```bash
   cd provider
   python -m hospital.cli learn
   ```

## 🛠️ Testing the API

### Basic Health Check
```bash
curl http://localhost:8000/health
```

### Search Providers
```bash
# Search by specialty
curl "http://localhost:8000/api/v1/providers/search?specialty=Cardiology&state=NY&limit=3"

# Search by name
curl "http://localhost:8000/api/v1/providers/search?last_name=Smith&city=Boston"

# Search organizations
curl "http://localhost:8000/api/v1/providers/search?organization_name=Mayo&limit=5"
```

### Search Hospitals
```bash
# Search by name
curl "http://localhost:8000/api/v1/hospitals/search?name=Cleveland&limit=3"

# Search by location
curl "http://localhost:8000/api/v1/hospitals/search?city=Boston&state=MA"

# Get specific hospital by CCN
curl "http://localhost:8000/api/v1/hospitals/search?ccn=220001"
```

### Get Comprehensive Hospital Data
```bash
curl "http://localhost:8000/api/v1/hospitals/220001/comprehensive"
```

### Risk Analysis
```bash
curl "http://localhost:8000/api/v1/hospitals/220001/risk-analysis"
```

### Enhanced Search
```bash
curl "http://localhost:8000/api/v1/hospitals/enhanced-search?query=Johns%20Hopkins&include_google_data=true"
```

## 📊 Response Format

All API responses follow this standard format:

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "count": 10,  // Number of results (for search endpoints)
  "error": null,  // Error message if success=false
  "metadata": {
    "source": "NPPES",  // Data source
    "timestamp": "2024-01-01T00:00:00Z",
    // Additional metadata
  }
}
```

## 🚨 Error Handling

### Common HTTP Status Codes:
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error
- `503`: Service Unavailable (module not available)

### Error Response Example:
```json
{
  "detail": "CCN must be 6 digits"
}
```

## 🔗 Integration Examples

### Python Client Example
```python
import requests

# Search providers
response = requests.get(
    "http://localhost:8000/api/v1/providers/search",
    params={
        "specialty": "Cardiology",
        "state": "NY",
        "limit": 5
    }
)
data = response.json()
providers = data["data"]["providers"]

# Get hospital comprehensive data
response = requests.get(
    "http://localhost:8000/api/v1/hospitals/220001/comprehensive"
)
hospital_data = response.json()["data"]["hospital"]
```

### JavaScript/Node.js Example
```javascript
// Search hospitals
const response = await fetch(
  'http://localhost:8000/api/v1/hospitals/search?name=Mayo&limit=3'
);
const data = await response.json();
const hospitals = data.data.hospitals;

// Get risk analysis
const riskResponse = await fetch(
  'http://localhost:8000/api/v1/hospitals/220001/risk-analysis'
);
const riskData = await riskResponse.json();
```

## 🎯 Advanced Features

### 1. Filtering and Pagination
Most search endpoints support:
- `limit`: Control number of results
- Various filters (specialty, location, etc.)

### 2. Multi-source Data Integration
- **NPPES**: Government provider database
- **CMS**: Hospital quality and performance data  
- **Google Places**: Reviews, ratings, contact info
- **AI Predictions**: Star rating predictions
- **Risk Analysis**: Multi-domain risk assessment

### 3. Real-time Health Monitoring
The `/health` endpoint provides real-time status of all services and data sources.

## 🔒 Security Notes

- The API currently runs without authentication (development mode)
- For production use, implement proper authentication
- Configure CORS appropriately for your domain
- Secure API keys in environment variables

## 🆘 Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure virtual environment is activated and dependencies installed
2. **Service Unavailable**: Check if required data files exist in `provider/hospital/data/`
3. **Google API Issues**: Verify `GOOGLE_API_KEY` in environment variables
4. **Database Errors**: Run initial training with `python -m hospital.cli learn`

### Getting Help:
- Check API documentation at http://localhost:8000/docs
- Review logs in terminal where API server is running
- Verify system status at http://localhost:8000/api/v1/system/status
