from __future__ import annotations
import os
from pathlib import Path

# Target datasets and expected filename patterns inside ZIPs
TARGET_FILE_PATTERNS = {
    "complications_deaths": [
        "Complications_and_Deaths-Hospital.csv",
        "Complications and Deaths - Hospital.csv",
    ],
    "readmissions_deaths": [
        "Readmissions_and_Deaths-Hospital.csv",
        "Readmissions and Deaths - Hospital.csv",
    ],
    "hcahps": [
        "HCAHPS_-_Hospital.csv",
        "HCAHPS_Hospital.csv",
        "HCAHPS - Hospital.csv",
    ],
    "timely_effective": [
        "Timely_and_Effective_Care_-_Hospital.csv",
        "Timely_and_Effective_Care-Hospital.csv",
        "Timely and Effective Care - Hospital.csv",
    ],
    "overall_star": [
        "Overall_Hospital_Quality_Star_Rating.csv",
        "Overall Hospital Quality Star Rating.csv",
    ],
}

# Standard schema column names
METRICS_SCHEMA = [
    "ccn",
    "measure_id",
    "measure_name",
    "domain",
    "unit",
    "direction",
    "period_start",
    "period_end",
    "release",
    "value",
    "value_lo",
    "value_hi",
    "denominator",
    "compare_to_national",
    "reason",
    "facility_name",
    "state",
    "city",
    "zip",
]

STAR_SCHEMA = [
    "ccn",
    "period_start",
    "period_end",
    "release",
    "star_rating",
    "reason",
    "facility_name",
    "state",
    "city",
    "zip",
]

# Prediction/Evaluation schemas for DuckDB
PREDICTIONS_SCHEMA = [
    "ccn",
    "period_end",  # target period end
    "target_release",  # label like YYYY_MM (what we're predicting)
    "model_name",
    "prediction_type",  # 'direct_star' | 'composite_star'
    "pred_star",
    "conf_lo",
    "conf_hi",
    "prob_star_1",
    "prob_star_2",
    "prob_star_3",
    "prob_star_4",
    "prob_star_5",
    "generated_at",
]

EVALUATIONS_SCHEMA = [
    "ccn",
    "period_end",
    "target_release",
    "model_name",
    "prediction_type",
    "pred_star",
    "actual_star",
    "abs_error",
    "within_band",  # 1 if actual in [conf_lo, conf_hi]
    "evaluated_at",
]

METRICS_CATALOG_SCHEMA = [
    "measure_id",
    "measure_name",
    "domain",
    "unit",
    "direction",
]

REASON_MAP = {
    "Not Available": "Not Available",
    "Not Applicable": "Not Applicable",
    "N/A": "Not Available",
    "NA": "Not Available",
    "Low Volume": "Low Volume Suppressed",
    "Low Volume Suppressed": "Low Volume Suppressed",
    "Suppressed": "Suppressed",
    "Measure Not Applicable": "Not Applicable",
}

# Defaults resolve relative to the project root (one level above this package)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WAREHOUSE_DIR = os.environ.get("CMS_WAREHOUSE_DIR", str(PROJECT_ROOT / "warehouse"))
DEFAULT_REPORTS_DIR = os.environ.get("CMS_REPORTS_DIR", str(PROJECT_ROOT / "reports"))
