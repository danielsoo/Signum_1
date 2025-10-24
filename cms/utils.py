from __future__ import annotations
import re
from datetime import date
from typing import Iterable, Optional, Tuple

from dateutil import parser
import pandas as pd


def normalize_ccn(raw: str | int | None) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    digits = re.sub(r"\D+", "", s)
    if digits == "":
        return None
    return digits.zfill(6)[:6]


def parse_date(value: str | None) -> Optional[date]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return parser.parse(str(value), dayfirst=False).date()
    except Exception:
        return None


def safe_float(x: object) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(str(x).replace("%", "").replace(",", ""))
    except Exception:
        return None


def safe_int(x: object) -> Optional[int]:
    if x is None or x == "":
        return None
    try:
        return int(float(str(x).replace(",", "")))
    except Exception:
        return None


def find_first_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    lower_cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        cand_norm = cand.lower()
        if cand_norm in lower_cols:
            return lower_cols[cand_norm]
    # relaxed contains search
    for cand in candidates:
        for lc, orig in lower_cols.items():
            if cand.lower() in lc:
                return orig
    return None


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df


# ---------------------------
# Release label helpers
# ---------------------------

def parse_release_label(label: str) -> Optional[Tuple[int, int]]:
    """Parse a release label like 'YYYY_MM' into (year, month).

    Returns None if parsing fails.
    """
    if label is None:
        return None
    m = re.fullmatch(r"(20\d{2})[_-]?([01]\d)", str(label))
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2))
    if month < 1 or month > 12:
        return None
    return year, month


def format_release_label(year: int, month: int) -> str:
    """Format (year, month) to 'YYYY_MM' with zero-padded month."""
    return f"{year:04d}_{month:02d}"


def add_months_to_release(label: str, months: int = 1) -> Optional[str]:
    """Add months to a release label and return the new label.

    If label parsing fails, returns None.
    """
    ym = parse_release_label(label)
    if ym is None:
        return None
    year, month = ym
    total = year * 12 + (month - 1) + months
    new_year = total // 12
    new_month = (total % 12) + 1
    return format_release_label(new_year, new_month)


def next_release_label(current_label: str) -> Optional[str]:
    """Convenience to get the next release label after current_label.

    This assumes monthly increments (YYYY_MM). If CMS releases are quarterly
    in your archive, you can call add_months_to_release(label, months=3).
    """
    return add_months_to_release(current_label, months=1)


# ---------------------------
# Domain direction helpers
# ---------------------------

def direction_from_domain(domain: Optional[str]) -> Optional[str]:
    """Infer direction label given a domain.

    Returns one of 'HIGHER_BETTER', 'LOWER_BETTER', or None when unknown.
    Heuristics:
      - PatientExperience: higher better (HCAHPS are top-box percentages)
      - Timely: higher better (many are compliance/percent; time-based are rarer)
      - Readmission/Mortality/Safety: lower better
    """
    if domain is None:
        return None
    d = str(domain)
    if d == "PatientExperience" or d == "Timely":
        return "HIGHER_BETTER"
    if d in {"Readmission", "Mortality", "Safety"}:
        return "LOWER_BETTER"
    return None

