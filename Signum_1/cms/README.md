# CMS Hospital Analytics System

An AI-powered hospital quality analytics system that predicts star ratings, evaluates model performance, and generates insights with automated reporting.

## 🚀 Features

- **ETL Pipeline**: Extract, transform, and load CMS hospital data
- **AI Predictions**: Markov-based star rating predictions for hospitals without official ratings
- **Model Evaluation**: Direction-based evaluation metrics (not absolute accuracy)
- **Insights Analysis**: Growth trends, domain analysis, and narrative generation
- **Automated Reports**: Beautiful HTML reports with consistent design
- **Dashboard**: Centralized view of all analytics reports
- **🔥 NEW: Unified Hospital Search**: 병원 검색 + Google + NPPES + CMS 통합 평가
- **🔥 NEW: Risk Analysis**: 사망률, 재발율 등 위험 지표 분석
- **🔥 NEW: Rating Comparison**: Google vs CMS 별점 비교 분석

## 🏃‍♂️ Quickstart

1) Install dependencies:

```bash
pip install -r cms/requirements.txt
```

2) Run ETL with ZIP files:

```bash
python -m cms.cli run /path/to/zip1.zip /path/to/zip2.zip
```

3) Generate predictions:

```bash
python -m cms.cli predict --generate-report
```

4) Evaluate model performance:

```bash
python -m cms.cli evaluate 2024_05 --generate-report
```

5) Generate insights:

```bash
python -m cms.cli insights --generate-report
```

6) Create dashboard:

```bash
python -m cms.cli dashboard
```

## 🔧 Environment Variables

Set these environment variables to customize paths:

```bash
export CMS_WAREHOUSE_DIR="/path/to/warehouse"  # Default: ./warehouse
export CMS_REPORTS_DIR="/path/to/reports"      # Default: ./reports
```

## 📋 Available Commands

| Command | Description | Options |
|---------|-------------|---------|
| `run <zip...>` | ETL: Extract → Transform → Load | `--warehouse-dir`, `--reports-dir` |
| `query <ccn>` | Query hospital data | `--start`, `--end`, `--domain` |
| `predict` | Generate star rating predictions | `--for-release`, `--generate-report` |
| `evaluate <release>` | Evaluate model performance | `--generate-report` |
| `insights` | Analyze hospital trends | `--release`, `--generate-report` |
| `dashboard` | Generate index dashboard | |
| `sample` | Extract training sample | `--out` |

## 🔍 Query Examples

```bash
# Query specific hospital
python -m cms.cli query 390048 --start 2023-01-01 --end 2024-12-31 --domain Mortality

# Generate predictions for next release
python -m cms.cli predict --for-release 2025_05 --generate-report

# Analyze insights for specific release
python -m cms.cli insights --release 2024_05 --generate-report
```

## 🗄️ Database Schema

### Core Tables
- **`hospital_metrics`**: Time series data with keys `(ccn, measure_id, period_end, release)`
- **`hospital_star`**: Star ratings with keys `(ccn, period_end, release)`
- **`metrics_catalog`**: Measure definitions with `(measure_id, measure_name, domain, unit, direction)`

### AI Tables
- **`star_predictions`**: AI predictions with probabilities and confidence bands
- **`star_evaluations`**: Model performance metrics (direction accuracy, rank correlation, etc.)
- **`hospital_insights`**: Growth trends, domain analysis, and narratives

## 📊 Report Types

| Report | Theme | Content |
|--------|-------|---------|
| **ETL** | 🔵 Blue | Data quality, missing rates, domain coverage |
| **Predict** | 🟢 Green | Star predictions, probabilities, confidence bands |
| **Evaluate** | 🟠 Orange | Direction accuracy, rank correlation, distribution similarity |
| **Insights** | 🟣 Purple | Growth index, domain trends, narratives |
| **Dashboard** | ⚪ White | All reports summary & navigation |

## 🧠 AI Model Details

### Prediction Model
- **Algorithm**: Markov Transition Model
- **Training**: Walk-forward validation using historical releases
- **Output**: Star rating predictions (1-5) with probabilities and 95% confidence bands
- **Scope**: Only hospitals without official ratings

### Evaluation Metrics
Since CMS star ratings are relative rankings, we use:
- **Direction Accuracy**: How well we predict improvement/decline
- **Rank Correlation**: Spearman correlation with actual rankings
- **Wasserstein Distance**: Distribution similarity
- **Smoothness**: Time series consistency
- **Domain RMSE**: Quantitative metrics accuracy

### Insights Analysis
- **Growth Index**: Sigmoid(trend_slope + recent_change) → 0-1 scale
- **Domain Trends**: Mortality, Readmission, Experience, Safety, Timely
- **Narratives**: Auto-generated performance stories

## 🧪 Testing

Run integration tests:

```bash
python test_integration.py
```

## 📁 Project Structure

```
Signum_1/
├── cms/                          # Main package
│   ├── __init__.py
│   ├── cli.py                    # Command-line interface
│   ├── model.py                  # AI prediction models
│   ├── evaluation.py             # Model evaluation metrics
│   ├── insights.py               # Growth analysis & narratives
│   ├── reports.py                # HTML report generation
│   ├── extract.py                # ZIP file extraction
│   ├── transform.py              # Data transformation
│   ├── load.py                   # Database loading
│   ├── validate.py               # Data validation
│   ├── constants.py              # Configuration constants
│   ├── utils.py                  # Utility functions
│   ├── query_tool.py             # Database queries
│   ├── requirements.txt          # Python dependencies
│   ├── README.md                 # This file
│   └── assets/css/               # Report styling
│       ├── base.css
│       ├── theme_etl.css
│       ├── theme_predict.css
│       ├── theme_evaluate.css
│       ├── theme_insights.css
│       └── theme_index.css
├── warehouse/                    # Data storage (auto-created)
│   ├── hospital.duckdb          # Main database
│   ├── hospital_metrics.parquet
│   ├── hospital_star.parquet
│   └── metrics_catalog.parquet
├── reports/                      # HTML reports (auto-created)
│   ├── index.html               # Dashboard
│   ├── etl_YYYY_MM.html        # ETL reports
│   ├── predict_YYYY_MM.html    # Prediction reports
│   ├── evaluate_YYYY_MM.html    # Evaluation reports
│   ├── insights_YYYY_MM.html    # Insights reports
│   └── assets/css/              # Report assets
├── test_integration.py          # Integration tests
├── test_structure.py            # Structure validation
└── cms/                         # CMS analytics system
    ├── unified_service.py       # 🔥 통합 서비스 (Google + NPPES + CMS)
    ├── search_engine.py         # 🔥 병원 검색 엔진
    ├── risk_analyzer.py         # 🔥 위험 지표 분석
    ├── rating_comparator.py     # 🔥 Google vs CMS 별점 비교
    └── ...
```

## 🔧 Configuration

Environment variables:
- `CMS_WAREHOUSE_DIR`: Data warehouse location (default: `./warehouse`)
- `CMS_REPORTS_DIR`: Reports output location (default: `./reports`)

## 📝 Notes

- Release detection from ZIP filenames (e.g., `2025_08`)
- Missing/footnote reasons standardized
- Upsert policy prevents duplicates
- All reports follow consistent design patterns
