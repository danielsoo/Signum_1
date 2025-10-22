from __future__ import annotations
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .constants import TARGET_FILE_PATTERNS
from .utils import clean_column_names


@dataclass(frozen=True)
class ExtractedFrame:
    dataset_key: str
    release: str
    source_zip: str
    inner_name: str
    frame: pd.DataFrame


def _infer_release_from_zip(zip_path: str) -> str:
    """Infer release as YYYY_MM from the zip filename.

    Accepts patterns like:
    - hospitals_08_2025.zip -> 2025_08
    - cms_2025-08_provider.zip -> 2025_08
    - 2024_12_anything.zip -> 2024_12
    Fallback: 'unknown'.
    """
    name = os.path.basename(zip_path)
    # Try YYYY[_-]MM first
    m = re.search(r"(20\d{2})[._-]?(0[1-9]|1[0-2])", name)
    if m:
        year, month = m.group(1), m.group(2)
        return f"{year}_{month}"
    # Try MM[_-]YYYY
    m = re.search(r"(0[1-9]|1[0-2])[._-]?(20\d{2})", name)
    if m:
        month, year = m.group(1), m.group(2)
        return f"{year}_{month}"
    return "unknown"


def _match_dataset(inner_name: str) -> Optional[str]:
    lower = inner_name.lower()
    for key, patterns in TARGET_FILE_PATTERNS.items():
        for pat in patterns:
            if pat.lower() in lower:
                return key
    return None


def _read_csv_from_zip(zf: zipfile.ZipFile, inner_name: str) -> pd.DataFrame:
    # Try utf-8-sig then latin-1 as fallback
    with zf.open(inner_name) as f:
        try:
            df = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        except Exception:
            f2 = zf.open(inner_name)
            df = pd.read_csv(f2, dtype=str, encoding="latin-1")
    return clean_column_names(df)


def extract_from_zips(zip_paths: Iterable[str]) -> List[ExtractedFrame]:
    """Scan provided ZIPs and extract target CSVs into data frames.

    Returns a list of ExtractedFrame with dataset key, release label and content.
    """
    results: List[ExtractedFrame] = []
    for zip_path in zip_paths:
        if not os.path.exists(zip_path):
            continue
        try:
            release = _infer_release_from_zip(zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    dataset_key = _match_dataset(info.filename)
                    if dataset_key is None:
                        continue
                    try:
                        df = _read_csv_from_zip(zf, info.filename)
                    except Exception:
                        continue
                    results.append(
                        ExtractedFrame(
                            dataset_key=dataset_key,
                            release=release,
                            source_zip=zip_path,
                            inner_name=info.filename,
                            frame=df,
                        )
                    )
        except zipfile.BadZipFile:
            continue
    return results
