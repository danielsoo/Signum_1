# 📋 SIGNUM AWS Deployment Checklist

Complete checklist for deploying SIGNUM Healthcare API to AWS.

---

## 📦 Files & Libraries Required

### 1. Core Application Files

#### Must Include:
```
✅ api_server.py                    # Main FastAPI application
✅ requirements-api.txt             # Python dependencies
✅ load_data.py                     # Data loading script
✅ .env (template)                  # Environment variables template
✅ provider/                        # Core package directory
   ├── common/                      # Shared utilities
   ├── google/                      # Google Places integration
   ├── government/                  # NPPES/CMS clients
   └── hospital/                    # Hospital analytics engine
      ├── extract.py
      ├── transform.py
      ├── load.py
      ├── model.py
      ├── search_engine.py
      ├── risk_analyzer.py
      ├── interactive_search.py
      └── warehouse/                # DuckDB database (generated)
```

#### Optional but Recommended:
```
✅ README.md                        # Project documentation
✅ API_DOCUMENTATION.md             # API usage guide
✅ example_client.py                # API client examples
✅ test_api.py                      # API tests
✅ test_imports.py                  # Import validation
```

#### Exclude from Upload:
```
❌ .venv/                          # Virtual environment (recreate on server)
❌ __pycache__/                    # Python cache
❌ .git/                           # Git history (optional)
❌ *.pyc                           # Compiled Python files
❌ .DS_Store                       # macOS files
❌ .vscode/                        # Editor config (optional)
```

---

## 📊 Hospital Dataset Files

### Required CSV Files (from `hospitals_current_data/`)

#### Core Files (Essential):
```
✅ Hospital_General_Information.csv              # Hospital metadata, star ratings
✅ Complications_and_Deaths-Hospital.csv         # Mortality/complications data
✅ HCAHPS-Hospital.csv                          # Patient satisfaction
✅ Timely_and_Effective_Care-Hospital.csv       # Care quality metrics
✅ Unplanned_Hospital_Visits-Hospital.csv       # Readmissions
```

#### Additional Quality Files (Recommended):
```
✅ Healthcare_Associated_Infections-Hospital.csv  # Infection rates
✅ Medicare_Hospital_Spending_Per_Patient-Hospital.csv
✅ Health_Equity-Hospital.csv
✅ Maternal_Health-Hospital.csv
```

#### Reference Files:
```
✅ Complications_and_Deaths-National.csv         # National benchmarks
✅ Complications_and_Deaths-State.csv            # State benchmarks
✅ HCAHPS-National.csv
✅ HCAHPS-State.csv
✅ Measure_Dates.csv                            # Data currency info
```

#### Optional Files (for enhanced features):
```
⚪ ASC_Facility.csv                              # Ambulatory Surgery Centers
⚪ CJR_Quality_Reporting_January_2025_Production_File.csv
⚪ FY_2025_HAC_Reduction_Program_Hospital.csv
⚪ hvbp_*.csv                                    # Value-Based Purchasing
⚪ Birthing_Friendly_Hospitals_Geocoded.csv
```

### Dataset Size:
- **Minimum Required**: ~50 MB
- **Full Dataset**: ~500 MB
- **S3 Storage Cost**: ~$0.01-0.10/month

---

## 🐍 Python Dependencies

### Core Framework (requirements-api.txt)

```txt
# Web Framework
fastapi==0.104.1                  # Modern web framework
uvicorn[standard]==0.24.0         # ASGI server
pydantic==2.5.0                   # Data validation

# CORS & Middleware
python-multipart==0.0.6           # Form data support

# Configuration
python-dotenv==1.0.0              # Environment variables

# HTTP Clients
httpx==0.25.2                     # Async HTTP client
requests==2.31.0                  # Standard HTTP client

# Data Processing
pandas>=1.5.0                     # Data manipulation
numpy>=1.24.0                     # Numerical computing
scipy>=1.11.0                     # Scientific computing

# Database
duckdb>=0.9.0                     # Embedded analytics DB

# Visualization & Reporting (optional)
matplotlib>=3.7.0                 # For chart generation
seaborn>=0.12.0                  # Statistical visualizations

# Logging
structlog==23.2.0                 # Structured logging

# Security (optional)
passlib[bcrypt]==1.7.4            # Password hashing
python-jose[cryptography]==3.3.0  # JWT tokens

# Development (optional)
pytest==7.4.3                     # Testing
pytest-asyncio==0.21.1            # Async testing
black==23.11.0                    # Code formatting
isort==5.12.0                     # Import sorting

# CLI Enhancement (used in hospital module)
rich>=13.0.0                      # Rich terminal output
```

### Full Dependency Tree:

#### Tier 1 - Critical (App won't run without):
- fastapi
- uvicorn
- pydantic
- pandas
- numpy
- duckdb

#### Tier 2 - Important (Features may fail):
- httpx / requests (for external APIs)
- python-dotenv (for config)
- scipy (for statistical analysis)

#### Tier 3 - Optional (Enhanced features):
- structlog (better logging)
- matplotlib/seaborn (visualization)
- rich (CLI prettiness)
- passlib/python-jose (auth)

---

## 🔐 Environment Variables & Secrets

### Required Variables:

```bash
# .env file (create on server)

# Data Paths (REQUIRED)
WAREHOUSE_DIR=/home/ubuntu/Signum_1/provider/hospital/warehouse
DATA_DIR=/home/ubuntu/Signum_1/hospitals_current_data

# Server Configuration (REQUIRED)
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# CORS Settings (REQUIRED for production)
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
# OR for development:
# CORS_ORIGINS=*

# External API Keys (OPTIONAL)
GOOGLE_API_KEY=your_google_places_api_key_if_applicable
# Note: Google Places API is optional, NPPES is free

# Database (auto-configured)
DUCKDB_PATH=/home/ubuntu/Signum_1/provider/hospital/warehouse/hospital_data.duckdb
```

### AWS Secrets Manager (Production):

```bash
# Store sensitive data in AWS Secrets Manager
aws secretsmanager create-secret \
  --name signum/production/config \
  --secret-string '{
    "GOOGLE_API_KEY": "your-key-here",
    "API_SECRET_KEY": "random-secret-key",
    "DATABASE_ENCRYPTION_KEY": "another-secret"
  }'
```

---

## 📂 Directory Structure on AWS

### EC2 Instance Layout:

```
/home/ubuntu/
├── Signum_1/                              # Main application
│   ├── api_server.py
│   ├── load_data.py
│   ├── requirements-api.txt
│   ├── .env                               # Environment config
│   ├── .venv/                             # Python virtual env
│   ├── provider/                          # Core package
│   │   ├── common/
│   │   ├── google/
│   │   ├── government/
│   │   └── hospital/
│   │       ├── warehouse/                 # DuckDB database
│   │       │   ├── hospital_data.duckdb
│   │       │   ├── *.parquet             # Data files
│   │       │   └── models/               # ML models
│   │       └── reports/                   # Generated reports
│   └── hospitals_current_data/            # CSV datasets
│       ├── Hospital_General_Information.csv
│       ├── Complications_and_Deaths-Hospital.csv
│       └── ... (other CSV files)
├── logs/                                  # Application logs
│   └── signum_api.log
└── backups/                               # Database backups
    └── warehouse_backup_20251105.tar.gz
```

### S3 Bucket Structure:

```
s3://signum-hospital-data/
├── hospitals_current_data/                # Source datasets
│   ├── Hospital_General_Information.csv
│   ├── Complications_and_Deaths-Hospital.csv
│   └── ... (all CSV files)
└── backups/                               # Database backups
    ├── warehouse_backup_20251101.tar.gz
    ├── warehouse_backup_20251102.tar.gz
    └── ...

s3://signum-models/                        # Trained ML models (optional)
├── star_predictor_v1.pkl
└── risk_analyzer_v1.pkl
```

---

## 🚀 Pre-Deployment Steps

### 1. Prepare Local Files

```bash
cd /Users/harshmaheshwari/development/Signum_1

# Create deployment package (without .venv)
tar -czf signum_deploy.tar.gz \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='.DS_Store' \
  --exclude='*.ipynb_checkpoints' \
  .

# Verify package
tar -tzf signum_deploy.tar.gz | head -20
```

### 2. Upload Dataset to S3

```bash
# Create S3 bucket
aws s3 mb s3://signum-hospital-data-$(date +%Y%m%d) --region us-east-1

# Upload data
aws s3 sync hospitals_current_data/ \
  s3://signum-hospital-data-$(date +%Y%m%d)/hospitals_current_data/ \
  --storage-class STANDARD

# Verify
aws s3 ls s3://signum-hospital-data-$(date +%Y%m%d)/hospitals_current_data/ --recursive --human-readable
```

### 3. Create .env Template

```bash
# Create .env.template (for documentation)
cat > .env.template << 'EOF'
# SIGNUM API Configuration Template
# Copy to .env and fill in values

# Data Paths
WAREHOUSE_DIR=/home/ubuntu/Signum_1/provider/hospital/warehouse
DATA_DIR=/home/ubuntu/Signum_1/hospitals_current_data

# Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=*

# External APIs (optional)
GOOGLE_API_KEY=

# Database
DUCKDB_PATH=${WAREHOUSE_DIR}/hospital_data.duckdb
EOF
```

---

## ✅ Deployment Validation

### Phase 1: File Upload Verification

```bash
# On EC2 instance
ls -lh /home/ubuntu/Signum_1/
ls -lh /home/ubuntu/Signum_1/hospitals_current_data/*.csv | wc -l
# Should show ~40+ CSV files
```

### Phase 2: Dependency Installation

```bash
source /home/ubuntu/Signum_1/.venv/bin/activate
pip list | grep -E "(fastapi|uvicorn|pandas|duckdb)"
# All should be installed
```

### Phase 3: Data Loading

```bash
cd /home/ubuntu/Signum_1
python load_data.py
# Should complete without errors
ls -lh provider/hospital/warehouse/
# Should show hospital_data.duckdb and *.parquet files
```

### Phase 4: API Health Check

```bash
# Start API
uvicorn api_server:app --host 0.0.0.0 --port 8000 &

# Test endpoints
curl http://localhost:8000/health
# Expected: {"status":"healthy","timestamp":"..."}

curl http://localhost:8000/api/v1/hospitals/search?query=Mayo&limit=5
# Expected: JSON array of hospitals

# Stop test server
pkill uvicorn
```

### Phase 5: Service Validation

```bash
# Start systemd service
sudo systemctl start signum-api
sudo systemctl status signum-api
# Should show "active (running)"

# Check logs
sudo journalctl -u signum-api -n 50
# Should show startup messages, no errors
```

### Phase 6: External Access

```bash
# Get public IP
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Test from local machine
curl http://$EC2_IP:8000/health
curl http://$EC2_IP:8000/docs
# Should return API documentation HTML
```

---

## 🔍 Post-Deployment Monitoring

### Daily Checks:

```bash
# Check service status
sudo systemctl status signum-api

# Check disk usage
df -h

# Check logs for errors
sudo journalctl -u signum-api --since "1 hour ago" | grep -i error

# Check memory usage
free -h

# Check CPU usage
top -bn1 | head -20
```

### Weekly Tasks:

```bash
# Update OS packages
sudo apt update && sudo apt upgrade -y

# Backup database
/home/ubuntu/backup.sh

# Review CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxx \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average
```

---

## 📊 File Size Reference

| Item | Size | Notes |
|------|------|-------|
| Core Python code | ~5 MB | provider/ directory |
| requirements-api.txt | ~1 KB | Dependency list |
| Hospital CSV data | ~500 MB | All datasets |
| DuckDB database | ~300 MB | After loading |
| Virtual environment | ~200 MB | Recreate on server |
| Total deployment | ~800 MB | Excluding .venv |

---

## 🆘 Troubleshooting Checklist

### Problem: API won't start

```bash
✓ Check Python version: python3 --version (need 3.9+)
✓ Check virtual env: source .venv/bin/activate
✓ Check dependencies: pip install -r requirements-api.txt
✓ Check logs: sudo journalctl -u signum-api -n 100
✓ Check port: sudo lsof -i :8000
```

### Problem: Data loading fails

```bash
✓ Check CSV files exist: ls hospitals_current_data/*.csv
✓ Check permissions: chmod -R 755 hospitals_current_data/
✓ Check disk space: df -h
✓ Check warehouse dir: mkdir -p provider/hospital/warehouse
```

### Problem: External APIs not working

```bash
✓ Check .env file: cat .env | grep API_KEY
✓ Check internet: ping google.com
✓ Check security group: Allow outbound HTTPS (443)
✓ Check IAM role: AWS credentials configured
```

### Problem: High memory usage

```bash
✓ Reduce workers: Change --workers 2 to --workers 1
✓ Add swap: See AWS_DEPLOYMENT_GUIDE.md
✓ Upgrade instance: t3.small → t3.medium
✓ Monitor: htop or free -h
```

---

## 📋 Final Pre-Launch Checklist

- [ ] All required CSV files uploaded to S3
- [ ] S3 bucket permissions configured
- [ ] EC2 instance launched (right size)
- [ ] Security groups allow ports 22, 80, 443, 8000
- [ ] Code deployed to /home/ubuntu/Signum_1
- [ ] Virtual environment created and activated
- [ ] Dependencies installed from requirements-api.txt
- [ ] .env file created with correct paths
- [ ] Dataset downloaded from S3
- [ ] load_data.py executed successfully
- [ ] DuckDB database created
- [ ] API tested locally (curl localhost:8000/health)
- [ ] Systemd service configured
- [ ] Service enabled and started
- [ ] Nginx configured (if using)
- [ ] SSL certificate installed (if using domain)
- [ ] API accessible externally (curl http://PUBLIC_IP:8000/health)
- [ ] API documentation accessible (/docs)
- [ ] CloudWatch monitoring enabled
- [ ] Backup script configured
- [ ] Cost alerts set up
- [ ] Security groups reviewed
- [ ] IAM roles least-privilege
- [ ] Logs being collected

---

**Completion Time Estimate**: 2-4 hours for first deployment
**Difficulty**: Intermediate
**Prerequisites**: Basic AWS, Linux, Python knowledge

---

*Last Updated: November 2025*
