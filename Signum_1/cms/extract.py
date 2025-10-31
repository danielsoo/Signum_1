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
    """파일명으로 데이터셋 타입 매칭"""
    lower = inner_name.lower()
    for key, patterns in TARGET_FILE_PATTERNS.items():
        for pat in patterns:
            if pat.lower() in lower:
                return key
    return None


def _match_dataset_by_columns(df: pd.DataFrame) -> Optional[str]:
    """컬럼명으로 데이터셋 타입 매칭 (파일명 매칭 실패 시 사용)"""
    if df.empty or len(df.columns) == 0:
        return None
    
    cols_str = ' '.join([str(c).lower() for c in df.columns])
    
    # Veterans Health Administration 데이터는 별도 처리 (별점 아님)
    if 'veterans health administration' in cols_str:
        return None

    # HCAHPS - "hcahps", "patient experience" 키워드
    if any(k in cols_str for k in ['hcahps', 'patient experience', 'patient survey']):
        return 'hcahps'
    
    # Overall Star Rating - General information table
    if (
        'hospital overall rating' in cols_str
        and 'hospital overall rating footnote' in cols_str
        and 'hospital type' in cols_str
        and 'emergency services' in cols_str
    ):
        return 'overall_star'
    
    # Hospital General Information 파일에는 위 컬럼이 존재하지만 HCAHPS/HVBP 테이블에는 없음
    
    # Complications and Deaths
    if any(k in cols_str for k in ['complication', 'surgical complication', 'deaths complication']):
        return 'complications_deaths'
    
    # Readmissions and Deaths
    if any(k in cols_str for k in ['readmission', 'readmit']):
        return 'readmissions_deaths'
    
    # Timely and Effective Care
    if any(k in cols_str for k in ['timely', 'effective care', 'timely and effective']):
        return 'timely_effective'
    
    return None


def _is_zip_file(filename: str) -> bool:
    """파일명이 ZIP 파일인지 확인"""
    return filename.lower().endswith('.zip')


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
    """Scan provided ZIPs or directories and extract target CSVs into data frames.
    
    - Supports ZIP files (including nested ZIPs)
    - Supports directories: recursively finds *.csv and processes them
    
    Returns a list of ExtractedFrame with dataset key, release label and content.
    """
    results: List[ExtractedFrame] = []
    for zip_path in zip_paths:
        if not os.path.exists(zip_path):
            continue
        # 1) Directory support: walk and parse CSV files directly
        if os.path.isdir(zip_path):
            try:
                # release는 폴더명 또는 상위 폴더명에서 추론 시도
                release = _infer_release_from_zip(zip_path)
                for root, _, files in os.walk(zip_path):
                    for fn in files:
                        if not fn.lower().endswith('.csv'):
                            continue
                        full_path = os.path.join(root, fn)
                        # 파일명으로 매칭
                        dataset_key = _match_dataset(fn)
                        # 매칭 실패 시 헤더 기반 판별
                        if dataset_key is None:
                            try:
                                try:
                                    df_sample = pd.read_csv(full_path, nrows=1, dtype=str, encoding="utf-8-sig")
                                except Exception:
                                    df_sample = pd.read_csv(full_path, nrows=1, dtype=str, encoding="latin-1")
                                dataset_key = _match_dataset_by_columns(df_sample)
                            except Exception:
                                dataset_key = None
                        if dataset_key is None:
                            continue
                        # 전체 읽기
                        try:
                            try:
                                df = pd.read_csv(full_path, dtype=str, encoding="utf-8-sig")
                            except Exception:
                                df = pd.read_csv(full_path, dtype=str, encoding="latin-1")
                            df = clean_column_names(df)
                            results.append(
                                ExtractedFrame(
                                    dataset_key=dataset_key,
                                    release=release,
                                    source_zip=zip_path,
                                    inner_name=os.path.relpath(full_path, start=zip_path),
                                    frame=df,
                                )
                            )
                        except Exception:
                            continue
            except Exception:
                continue
            # 다음 입력 경로로 계속
            continue

        # 2) ZIP support (including nested zips)
        try:
            release = _infer_release_from_zip(zip_path)
            
            # 먼저 직접 CSV 찾기 시도
            found_direct = False
            with zipfile.ZipFile(zip_path, "r") as zf:
                inner_files = [info for info in zf.infolist() if not info.is_dir()]
                
                # CSV 파일 직접 찾기
                for info in inner_files:
                    if _is_zip_file(info.filename):
                        continue  # ZIP 파일은 나중에 처리
                    
                    # 먼저 파일명으로 매칭 시도
                    dataset_key = _match_dataset(info.filename)
                    
                    # 파일명 매칭 실패 시 CSV 내용으로 매칭 시도
                    if dataset_key is None and info.filename.lower().endswith('.csv'):
                        try:
                            # CSV 헤더만 읽어서 컬럼 확인
                            with zf.open(info.filename) as f:
                                try:
                                    df_sample = pd.read_csv(f, nrows=1, dtype=str, encoding="utf-8-sig")
                                except Exception:
                                    # 파일을 다시 열어서 latin-1로 시도
                                    with zf.open(info.filename) as f2:
                                        df_sample = pd.read_csv(f2, nrows=1, dtype=str, encoding="latin-1")
                            dataset_key = _match_dataset_by_columns(df_sample)
                        except Exception:
                            pass  # 읽기 실패하면 스킵
                    
                    if dataset_key is None:
                        continue
                    
                    try:
                        df = _read_csv_from_zip(zf, info.filename)
                        found_direct = True
                        results.append(
                            ExtractedFrame(
                                dataset_key=dataset_key,
                                release=release,
                                source_zip=zip_path,
                                inner_name=info.filename,
                                frame=df,
                            )
                        )
                    except Exception:
                        continue
                
                # 직접 CSV를 못 찾았으면 중첩 ZIP 처리
                if not found_direct:
                    for info in inner_files:
                        if not _is_zip_file(info.filename):
                            continue
                        
                        # 중첩 ZIP 파일 추출 및 처리
                        try:
                            import tempfile
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # 내부 ZIP을 임시 디렉토리에 추출
                                inner_zip_path = os.path.join(temp_dir, os.path.basename(info.filename))
                                with zf.open(info.filename) as source, open(inner_zip_path, 'wb') as target:
                                    target.write(source.read())
                                
                                # 중첩 ZIP 처리
                                with zipfile.ZipFile(inner_zip_path, "r") as inner_zf:
                                    for inner_info in inner_zf.infolist():
                                        if inner_info.is_dir():
                                            continue
                                        
                                        # 먼저 파일명으로 매칭 시도
                                        dataset_key = _match_dataset(inner_info.filename)
                                        
                                        # 파일명 매칭 실패 시 CSV 내용으로 매칭 시도
                                        if dataset_key is None and inner_info.filename.lower().endswith('.csv'):
                                            try:
                                                with inner_zf.open(inner_info.filename) as f:
                                                    try:
                                                        df_sample = pd.read_csv(f, nrows=1, dtype=str, encoding="utf-8-sig")
                                                    except Exception:
                                                        # 파일을 다시 열어서 latin-1로 시도
                                                        with inner_zf.open(inner_info.filename) as f2:
                                                            df_sample = pd.read_csv(f2, nrows=1, dtype=str, encoding="latin-1")
                                                dataset_key = _match_dataset_by_columns(df_sample)
                                            except Exception:
                                                pass
                                        
                                        if dataset_key is None:
                                            continue
                                        
                                        try:
                                            df = _read_csv_from_zip(inner_zf, inner_info.filename)
                                            results.append(
                                                ExtractedFrame(
                                                    dataset_key=dataset_key,
                                                    release=release,
                                                    source_zip=zip_path,
                                                    inner_name=f"{info.filename}/{inner_info.filename}",
                                                    frame=df,
                                                )
                                            )
                                        except Exception:
                                            continue
                        except Exception:
                            # 중첩 ZIP 처리 실패 시 무시하고 계속
                            continue
                            
        except zipfile.BadZipFile:
            continue
        except Exception:
            # 기타 오류는 무시하고 계속
            continue
            
    return results
