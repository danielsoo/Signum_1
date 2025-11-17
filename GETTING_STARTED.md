# 🚀 Getting Started with SIGNUM API

## ⚠️ Current Issue: No Hospital Data

Your API is running, but you're getting empty results because **the hospital database hasn't been created yet**.

## 📥 Step 1: Download CMS Hospital Data

You need to download hospital quality data from CMS (Centers for Medicare & Medicaid Services):

### Option A: Download from CMS Website
1. Go to: https://data.cms.gov/provider-data/topics/hospitals/
2. Look for "Hospital General Information" dataset
3. Download the ZIP file(s) for recent quarters (e.g., 2024 Q3, Q4)

### Option B: Use Direct Links (Example)
```bash
# Create data directory
mkdir -p provider/hospital/data
cd provider/hospital/data

# Download recent CMS data (example - check for latest URLs)
# These are example URLs - check CMS website for current data
wget https://data.cms.gov/provider-data/sites/default/files/archive/Hospitals/2024_Q3/Hospital_General_Information.zip
```

## 🔧 Step 2: Run ETL Process

Once you have the ZIP file(s), load them into the database:

```bash
# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH="$(pwd):$(pwd)/provider"

# Run ETL with your downloaded ZIP file(s)
python -m provider.hospital.cli run provider/hospital/data/Hospital_General_Information.zip
```

This will:
- Extract hospital data from the ZIP
- Transform it into standardized format
- Load it into DuckDB database at `provider/hospital/warehouse/hospital.duckdb`

## 🧪 Step 3: Test the API

After ETL completes, test your searches:

```bash
# Search by city
curl "http://localhost:8000/api/v1/hospitals/search?city=New%20York&state=NY&limit=10"

# Search by name
curl "http://localhost:8000/api/v1/hospitals/search?name=Memorial&limit=10"

# Enhanced search with predictions
curl "http://localhost:8000/api/v1/hospitals/search?name=General&include_predictions=true&limit=5"
```

## 🔍 Alternative: Test with NPPES Provider Search

While you don't have hospital data yet, you can still test the **NPPES provider search** which works without any data loading:

```bash
# Search for doctors/providers by name
curl "http://localhost:8000/api/v1/providers/search?first_name=John&last_name=Smith&limit=5"

# Search providers in a city
curl "http://localhost:8000/api/v1/providers/search?city=New%20York&state=NY&limit=10"

# Search by specialty
curl "http://localhost:8000/api/v1/providers/search?taxonomy_description=Cardiology&limit=5"
```

## 📊 Step 4: Generate AI Predictions (Optional)

After loading hospital data, you can generate AI-powered star rating predictions:

```bash
# Generate predictions for hospitals without official ratings
python -m provider.hospital.cli predict --generate-report

# Evaluate prediction model
python -m provider.hospital.cli evaluate 2024_05 --generate-report

# Generate insights and trends
python -m provider.hospital.cli insights --generate-report
```

## 🗂️ Data Structure After Setup

```
provider/hospital/
├── data/                                  # Your downloaded ZIP files
│   └── Hospital_General_Information.zip
├── warehouse/                             # Auto-created by ETL
│   ├── hospital.duckdb                   # Main database
│   ├── hospital_metrics.parquet
│   └── hospital_star.parquet
└── reports/                               # Auto-created reports
    ├── index.html
    └── etl_2024_12.html
```

## ❓ Troubleshooting

### "No results found"
- **Cause**: Database doesn't exist or is empty
- **Solution**: Run ETL with CMS data ZIP files (see Step 2)

### "Module not found" errors
- **Cause**: Virtual environment not activated or PYTHONPATH not set
- **Solution**: 
  ```bash
  source .venv/bin/activate
  export PYTHONPATH="$(pwd):$(pwd)/provider"
  ```

### "Google client failed"
- **Cause**: Missing or invalid Google Maps API key
- **Solution**: This is optional. The API works without it, you just won't get Google Places data

## 🎯 Quick Test Without Hospital Data

If you want to test the API immediately without downloading hospital data, use the **NPPES endpoints**:

```python
import requests

# Search for healthcare providers (works without hospital data)
response = requests.get(
    "http://localhost:8000/api/v1/providers/search",
    params={
        "city": "New York",
        "state": "NY",
        "limit": 10
    }
)

print(response.json())
```

## 📚 Next Steps

1. **Download CMS data** (see Step 1)
2. **Run ETL** to populate database (see Step 2)
3. **Test hospital search** endpoints (see Step 3)
4. **Optional**: Add Google Maps API key for enhanced search
5. **Optional**: Generate AI predictions and reports (see Step 4)

## 🔗 Useful Links

- **CMS Hospital Data**: https://data.cms.gov/provider-data/topics/hospitals/
- **NPPES Provider Data**: https://npiregistry.cms.hhs.gov/
- **API Documentation**: http://localhost:8000/docs
- **Project README**: provider/hospital/README.md
