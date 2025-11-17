from __future__ import annotations
import re
from datetime import date
from typing import Iterable, Optional

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
