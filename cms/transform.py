from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .constants import METRICS_SCHEMA, STAR_SCHEMA, REASON_MAP
from .utils import (
    find_first_column,
    normalize_ccn,
    parse_date,
    safe_float,
    safe_int,
)


@dataclass(frozen=True)
class Transformed:
    metrics: pd.DataFrame
    star: pd.DataFrame
    metrics_catalog: pd.DataFrame


# Column name candidates across files
CCN_CANDS = [
    "Provider ID",
    "CMS Certification Number (CCN)",
    "Facility ID",
    "Provider Number",
]
FACILITY_CANDS = ["Hospital Name", "Facility Name", "Provider Name"]
STATE_CANDS = ["State"]
CITY_CANDS = ["City"]
ZIP_CANDS = ["ZIP Code", "ZIP", "Zip Code"]
MEASURE_ID_CANDS = ["Measure ID", "MeasureID", "Measure Identifier"]
MEASURE_NAME_CANDS = ["Measure Name", "MeasureName"]
SCORE_CANDS = [
    "Score",
    "Rate",
    "Observed Rate",
    "Value",
    "Observed Value",
    "Score/Value",
]
LOWER_CANDS = [
    "Lower Estimate",
    "Lower Confidence Interval",
    "Lower CI",
    "Lower bound",
]
UPPER_CANDS = [
    "Upper Estimate",
    "Upper Confidence Interval",
    "Upper CI",
    "Upper bound",
]
DENOM_CANDS = [
    "Denominator",
    "Number of Cases",
    "Provider Denominator Count",
    "Denominator Count",
]
COMPARE_CANDS = [
    "Compared to National",
    "Compared to National Rate",
    "Comparison to National",
    "Compared to National benchmark",
]
FOOTNOTE_CANDS = ["Footnote", "Footnote Text", "Footnotes", "Footnote ID", "Footnote Symbol"]
START_CANDS = [
    "Start Date",
    "Measure Start Date",
    "Performance Period Start",
    "Start of Performance Period",
]
END_CANDS = [
    "End Date",
    "Measure End Date",
    "Performance Period End",
    "End of Performance Period",
]
STAR_VALUE_CANDS = [
    "Hospital overall rating",
    "Overall Hospital Rating",
    "Overall Rating",
]


def _std_reason(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "":
        return None
    # direct mapping
    if text in REASON_MAP:
        return REASON_MAP[text]
    # normalized matching
    lower = text.lower()
    for k, v in REASON_MAP.items():
        if k.lower() in lower:
            return v
    return "OTHER"


def _domain_from(dataset_key: str, measure_id: Optional[str], measure_name: Optional[str]) -> Optional[str]:
    if measure_id:
        mid = measure_id.upper()
        if mid.startswith("READM"):
            return "Readmission"
        if mid.startswith("MORT") or mid.startswith("COMP"):
            return "Mortality"
        if mid.startswith("PSI") or mid.startswith("HAI") or mid.startswith("HAC"):
            return "Safety"
        if mid.startswith("ED") or mid.startswith("OP") or mid.startswith("VTE"):
            return "Timely"
        if mid.startswith("HCAHPS") or mid.startswith("H_" ):
            return "PatientExperience"
    # fallback by dataset
    mapping = {
        "readmissions_deaths": "Readmission",
        "complications_deaths": "Mortality",
        "timely_effective": "Timely",
        "hcahps": "PatientExperience",
    }
    return mapping.get(dataset_key)


def _transform_metrics_like(df: pd.DataFrame, dataset_key: str, release: str) -> pd.DataFrame:
    df = df.copy()
    ccn_col = find_first_column(df, CCN_CANDS)
    measure_id_col = find_first_column(df, MEASURE_ID_CANDS)
    measure_name_col = find_first_column(df, MEASURE_NAME_CANDS)
    score_col = find_first_column(df, SCORE_CANDS)
    lo_col = find_first_column(df, LOWER_CANDS)
    hi_col = find_first_column(df, UPPER_CANDS)
    denom_col = find_first_column(df, DENOM_CANDS)
    compare_col = find_first_column(df, COMPARE_CANDS)
    foot_col = find_first_column(df, FOOTNOTE_CANDS)
    start_col = find_first_column(df, START_CANDS)
    end_col = find_first_column(df, END_CANDS)
    facility_col = find_first_column(df, FACILITY_CANDS)
    state_col = find_first_column(df, STATE_CANDS)
    city_col = find_first_column(df, CITY_CANDS)
    zip_col = find_first_column(df, ZIP_CANDS)

    out = pd.DataFrame({
        "ccn": df[ccn_col].map(normalize_ccn) if ccn_col else None,
        "measure_id": df[measure_id_col] if measure_id_col else None,
        "measure_name": df[measure_name_col] if measure_name_col else None,
        "domain": None,
        "unit": None,
        "direction": None,
        "period_start": df[start_col].map(parse_date) if start_col else None,
        "period_end": df[end_col].map(parse_date) if end_col else None,
        "release": release,
        "value": df[score_col].map(safe_float) if score_col else None,
        "value_lo": df[lo_col].map(safe_float) if lo_col else None,
        "value_hi": df[hi_col].map(safe_float) if hi_col else None,
        "denominator": df[denom_col].map(safe_int) if denom_col else None,
        "compare_to_national": df[compare_col] if compare_col else None,
        "reason": df[foot_col].map(_std_reason) if foot_col else None,
        "facility_name": df[facility_col] if facility_col else None,
        "state": df[state_col] if state_col else None,
        "city": df[city_col] if city_col else None,
        "zip": df[zip_col] if zip_col else None,
    })

    # infer domain row-wise
    out["domain"] = out.apply(
        lambda r: _domain_from(dataset_key, r.get("measure_id"), r.get("measure_name")), axis=1
    )

    # keep only schema columns
    out = out[[c for c in METRICS_SCHEMA if c in out.columns]].copy()
    return out


def _transform_star(df: pd.DataFrame, release: str) -> pd.DataFrame:
    df = df.copy()
    ccn_col = find_first_column(df, CCN_CANDS)
    facility_col = find_first_column(df, FACILITY_CANDS)
    state_col = find_first_column(df, STATE_CANDS)
    city_col = find_first_column(df, CITY_CANDS)
    zip_col = find_first_column(df, ZIP_CANDS)
    start_col = find_first_column(df, START_CANDS)
    end_col = find_first_column(df, END_CANDS)
    star_col = find_first_column(df, STAR_VALUE_CANDS)
    foot_col = find_first_column(df, FOOTNOTE_CANDS)

    out = pd.DataFrame({
        "ccn": df[ccn_col].map(normalize_ccn) if ccn_col else None,
        "period_start": df[start_col].map(parse_date) if start_col else None,
        "period_end": df[end_col].map(parse_date) if end_col else None,
        "release": release,
        "star_rating": df[star_col].map(safe_float) if star_col else None,
        "reason": df[foot_col].map(_std_reason) if foot_col else None,
        "facility_name": df[facility_col] if facility_col else None,
        "state": df[state_col] if state_col else None,
        "city": df[city_col] if city_col else None,
        "zip": df[zip_col] if zip_col else None,
    })

    out = out[[c for c in STAR_SCHEMA if c in out.columns]].copy()
    return out


def transform_all(extracted: List[Tuple[str, str, pd.DataFrame]]) -> Transformed:
    metrics_frames: List[pd.DataFrame] = []
    star_frames: List[pd.DataFrame] = []

    for dataset_key, release, df in extracted:
        if dataset_key == "overall_star":
            star_frames.append(_transform_star(df, release))
        else:
            metrics_frames.append(_transform_metrics_like(df, dataset_key, release))

    metrics = pd.concat(metrics_frames, ignore_index=True) if metrics_frames else pd.DataFrame(columns=[])
    star = pd.concat(star_frames, ignore_index=True) if star_frames else pd.DataFrame(columns=[])

    # metrics catalog from metrics
    if not metrics.empty:
        metrics_catalog = (
            metrics[["measure_id", "measure_name", "domain"]]
            .dropna(subset=["measure_id"]).drop_duplicates()
        )
        metrics_catalog["unit"] = None
        metrics_catalog["direction"] = None
    else:
        metrics_catalog = pd.DataFrame(columns=["measure_id", "measure_name", "domain", "unit", "direction"])

    return Transformed(metrics=metrics, star=star, metrics_catalog=metrics_catalog)
