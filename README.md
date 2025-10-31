# SIGNUM - Healthcare Provider Intelligence Platform

A comprehensive healthcare data platform that integrates multiple data sources (Google Places, NPPES, CMS) to provide intelligent hospital search, quality analysis, and risk assessment.

## 🏗️ Project Structure

```
signum/
├── provider/              # Main package - All provider-related modules
│   ├── common/           # Shared utilities and configurations
│   ├── google/           # Google Places API integration
│   ├── government/       # Government APIs (NPPES, CMS PDC)
│   └── hospital/         # Hospital data analytics & AI models
├── .venv/                # Python virtual environment
└── bootstrap.sh          # Legacy bootstrap script
```

---

## 📦 Provider Package Overview

### `provider/common/` - Shared Configuration
**Purpose**: Common utilities and configuration shared across all modules.

| File | Purpose |
|------|---------|
| `config.py` | Global configuration settings |
| `__init__.py` | Package initialization |

---

### `provider/google/` - Google Places API Integration
**Purpose**: Integrate Google Places API to search and retrieve hospital information with ratings and reviews.

| File | Purpose | Key Features |
|------|---------|--------------|
| `places_client_v1.py` | Google Places API v1 client | • Text search for hospitals<br>• Nearby search<br>• Place details retrieval<br>• Rating & review data |
| `usage_tracker.py` | API usage tracking | • Track API call counts<br>• Monitor quota usage<br>• Persist usage data in JSON |
| `feature_flags.py` | Feature toggle system | • Enable/disable API features<br>• Runtime configuration |
| `cli_google.py` | Command-line interface | • Interactive Google Places search<br>• Test API functionality |

**API Key Required**: Set `GOOGLE_API_KEY` in `.env` file.

---

### `provider/government/` - Government Healthcare APIs
**Purpose**: Access free government healthcare provider databases (NPPES, ClinicalTables, CMS PDC).

| File | Purpose | Key Features |
|------|---------|--------------|
| `clients_free.py` | Main client implementations | • **NPPESClient**: Search National Provider Identifier (NPI)<br>• **CMSPDCClient**: Find hospital affiliations<br>• **ClinicalTablesClient**: NIH provider search |
| `clinicaltables_client.py` | NIH ClinicalTables integration | • Search individual providers<br>• Search organizations<br>• Autocomplete support |
| `rate_limiter.py` | API rate limiting | • Token bucket algorithm<br>• Prevent API throttling<br>• Configurable rate limits |
| `http_utils.py` | HTTP utilities | • Retry logic<br>• Exponential backoff<br>• Request timeout handling |
| `cli.py` | Command-line interface | • Interactive provider search<br>• Multiple display modes |

**No API Key Required**: All government APIs are free and public.

---

### `provider/hospital/` - Hospital Analytics & AI Platform
**Purpose**: The core analytics engine - ETL pipeline, AI predictions, risk analysis, and interactive search.

#### 📂 Folder Structure
```
hospital/
├── data/              # ZIP files (CMS hospital data)
├── warehouse/         # DuckDB database & trained models
├── reports/           # Generated HTML reports
└── [Python modules]   # Core functionality
```

---

#### 🔧 Core Modules

##### **ETL Pipeline** (Extract, Transform, Load)

| File | Purpose | Key Features |
|------|---------|--------------|
| `extract.py` | Extract data from ZIP files | • Auto-detect CMS data files<br>• Parse multiple formats<br>• Release detection |
| `transform.py` | Transform to standard schema | • Normalize column names<br>• Standardize metrics<br>• Handle missing data |
| `load.py` | Load into DuckDB database | • Parquet export<br>• DuckDB upsert<br>• Index creation |
| `validate.py` | Data quality validation | • Missing rate analysis<br>• Data coverage reports<br>• Quality metrics |

##### **AI & Machine Learning**

| File | Purpose | Key Features |
|------|---------|--------------|
| `model.py` | AI prediction model | • **Markov Transition Model**<br>• Star rating predictions<br>• Confidence intervals<br>• Walk-forward validation |
| `evaluation.py` | Model performance evaluation | • Direction accuracy<br>• Rank correlation<br>• Wasserstein distance<br>• Domain RMSE |
| `sequential_trainer.py` | Automated training pipeline | • Auto-detect new data<br>• Sequential ETL → Train → Evaluate<br>• Skip processed files<br>• Progress tracking |
| `training_tracker.py` | Training state management | • Track processed files<br>• Store training history<br>• Resume from checkpoint |

##### **Analytics & Insights**

| File | Purpose | Key Features |
|------|---------|--------------|
| `insights.py` | Hospital growth analysis | • Growth index calculation<br>• Domain trend analysis<br>• Narrative generation |
| `risk_analyzer.py` | Risk assessment | • Mortality analysis<br>• Readmission rates<br>• Safety indicators<br>• Alert generation |
| `rating_comparator.py` | Rating comparison | • Google vs CMS rating comparison<br>• Consistency scoring<br>• Confidence analysis |

##### **Search & Discovery**

| File | Purpose | Key Features |
|------|---------|--------------|
| `search_engine.py` | Hospital search engine | • Fuzzy name search<br>• Location-based search<br>• Specialty filtering<br>• CCN lookup |
| `interactive_search.py` | Interactive search UI | • Multi-source integration (Google + NPPES + CMS)<br>• Rich terminal UI<br>• Distance calculation<br>• Rating display |
| `unified_service.py` | Unified API service | • Single entry point<br>• Combined data from all sources<br>• Comprehensive evaluation |

##### **Utilities**

| File | Purpose | Key Features |
|------|---------|--------------|
| `cli.py` | Main command-line interface | • `run`: ETL pipeline<br>• `learn`: Auto-training<br>• `predict`: Generate predictions<br>• `evaluate`: Model evaluation<br>• `insights`: Analytics<br>• `search`: Interactive search |
| `query_tool.py` | Database query utilities | • Metric queries<br>• Star rating queries<br>• Time range filtering |
| `constants.py` | Configuration constants | • File patterns<br>• Schema definitions<br>• Default paths<br>• Reason mapping |
| `utils.py` | Helper functions | • Date parsing<br>• String formatting<br>• Common utilities |

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd signum

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `provider/.env`:
```bash
# Google Places API (optional - for enhanced search)
GOOGLE_API_KEY=your_google_api_key_here

# Feature flags
FREE_APIS_OFFLINE=0  # Set to 1 to disable external API calls
```

### 3. Prepare Data

Place CMS hospital data ZIP files in `provider/hospital/data/`:
```bash
provider/hospital/data/
├── hospitals_01_2024.zip
├── hospitals_04_2024.zip
└── ... (more ZIP files)
```

### 4. Run Training (First Time)

```bash
cd provider
python -m hospital.cli learn
```

This will:
- Extract data from all ZIP files
- Transform to standard schema
- Load into DuckDB database
- Train AI models
- Generate predictions
- Create evaluation reports
- Generate insights

### 5. Interactive Search

```bash
cd provider
python -m hospital.cli search
```

Choose from:
1. **Hospital search** - Search by name
2. **Doctor search** - Find doctors and their hospital affiliations
3. **Location search** - Find hospitals by city/state
4. **Specialty search** - Filter by medical specialty

---

## 📊 Features

### 🔍 **Multi-Source Integration**
- **Google Places**: Real-time ratings & reviews
- **NPPES**: National Provider Identifier database
- **CMS**: Official Medicare hospital quality data

### 🤖 **AI Predictions**
- Predict future hospital star ratings
- Confidence intervals for predictions
- Direction accuracy (improvement/decline)

### ⚠️ **Risk Analysis**
- Mortality rates
- Readmission rates
- Patient safety indicators
- Automated alert generation

### 📈 **Growth Analytics**
- Hospital performance trends
- Domain-specific analysis
- Narrative insights
- Growth index scoring

### 🎨 **Beautiful Reports**
- HTML reports with charts
- Dashboard overview
- Color-coded themes
- Mobile-responsive design

---

## 🔧 Command Reference

### ETL & Data Management

```bash
# Run ETL on specific ZIP files
python -m hospital.cli run path/to/file1.zip path/to/file2.zip

# Auto-train from data/ folder (recommended)
python -m hospital.cli learn

# Force retrain all data
python -m hospital.cli learn --force

# Check training status
python -m hospital.cli status
```

### AI & Analytics

```bash
# Generate star rating predictions
python -m hospital.cli predict --generate-report

# Evaluate model performance
python -m hospital.cli evaluate 2024_05 --generate-report

# Generate insights
python -m hospital.cli insights --generate-report

# Create dashboard
python -m hospital.cli dashboard
```

### Search & Query

```bash
# Interactive search
python -m hospital.cli search

# Query specific hospital
python -m hospital.cli query 390048 --start 2023-01-01 --domain Mortality
```

### API Testing

```bash
# Test Google Places API
cd provider/google
python -m google.cli_google search "Mayo Clinic" "Rochester, MN"

# Test NPPES API
cd provider/government
python -m government.cli search --mode compact "Mayo Clinic"
```

---

## 📁 Data Files

### Input: `provider/hospital/data/`
Place CMS hospital ZIP files here. The system auto-detects:
- `hospitals_MM_YYYY.zip` - Regular releases
- `hos_revised_flatfiles_archive_MM_YYYY.zip` - Archive files

### Output: `provider/hospital/warehouse/`
- `hospital.duckdb` - Main database (DuckDB)
- `hospital_metrics.parquet` - Metrics data
- `hospital_star.parquet` - Star ratings
- `metrics_catalog.parquet` - Measure definitions
- `models/` - Trained AI models

### Reports: `provider/hospital/reports/`
- `index.html` - Dashboard
- `etl_YYYY_MM.html` - Data quality reports
- `predict_YYYY_MM.html` - Prediction reports
- `evaluate_YYYY_MM.html` - Evaluation reports
- `insights_YYYY_MM.html` - Analytics reports

---

## 🌐 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `GOOGLE_API_KEY` | Google Places API key | None (optional) |
| `YELP_API_KEY` | Yelp Fusion API key | None (optional) |
| `FREE_APIS_OFFLINE` | Disable external APIs | `0` (enabled) |
| `CMS_WAREHOUSE_DIR` | Custom warehouse path | `provider/hospital/warehouse` |
| `CMS_REPORTS_DIR` | Custom reports path | `provider/hospital/reports` |
| `DISABLE_AI` | Skip AI training steps | `0` (enabled) |

---

## 🧪 Architecture

### Data Flow

```
1. DATA INGESTION
   ZIP files → Extract → Transform → DuckDB

2. AI PIPELINE
   DuckDB → Feature Engineering → Model Training → Predictions

3. EVALUATION
   Predictions vs Actual → Metrics → Reports

4. INSIGHTS
   Trend Analysis → Growth Index → Narratives

5. SEARCH
   User Query → Multi-source Search → Unified Results
```

### AI Model Details

**Model Type**: Markov Transition Model
- Learns probability of star rating transitions
- Uses historical data to predict future ratings
- Provides confidence intervals
- Direction-based evaluation (not absolute accuracy)

**Evaluation Metrics**:
- Direction Accuracy: How often we correctly predict improvement/decline
- Rank Correlation: Spearman correlation with actual rankings
- Wasserstein Distance: Distribution similarity
- Domain RMSE: Quantitative metric accuracy

---

## 🤝 Contributing

### Code Style
- Python 3.8+
- Type hints encouraged
- Docstrings for public functions
- Follow existing patterns

### Testing
```bash
# Run tests (if available)
python -m pytest

# Validate data quality
python -m hospital.cli run test_data.zip --validate
```

---

## 📄 License

See `LICENSE` file for details.

---

## 🙋 Support

For questions or issues:
1. Check documentation in each module's docstrings
2. Review generated reports for data quality issues
3. Enable verbose logging: `export LOG_LEVEL=DEBUG`

---

## 🎯 Key Concepts

### **CCN (CMS Certification Number)**
- Unique 6-digit identifier for each hospital
- Primary key in CMS database
- Used to link data across sources

### **Star Rating (1-5 stars)**
- CMS overall hospital quality rating
- Updated quarterly
- Based on multiple quality domains

### **Domains**
- **Mortality**: Death rates for specific conditions
- **Readmission**: 30-day readmission rates
- **Safety**: Complications and infections
- **Patient Experience**: HCAHPS survey results
- **Timely Care**: Treatment timeliness

### **Release**
- Data snapshot identifier (e.g., `2024_05` = May 2024)
- CMS publishes quarterly updates
- Used for time-series analysis

---

## 🔮 Future Enhancements

- [ ] Web dashboard (React/Next.js)
- [ ] Real-time data updates
- [ ] Advanced ML models (Random Forest, Neural Networks)
- [ ] Geographic visualization
- [ ] Patient review sentiment analysis
- [ ] Hospital comparison tool
- [ ] API server (REST/GraphQL)

---

**Built with ❤️ for healthcare transparency and data-driven decision making.**

