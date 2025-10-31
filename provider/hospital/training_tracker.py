"""
Training Tracker - 학습 상태 추적 모듈

처리된 ZIP 파일과 릴리스를 추적하여 중복 처리를 방지하고 학습 상태를 관리합니다.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class TrainingTracker:
    """
    학습 상태를 추적하고 관리하는 클래스.
    
    기능:
    - 처리된 파일 목록 관리
    - 릴리스별 처리 상태 추적
    - 학습 상태 초기화
    """
    
    def __init__(self, warehouse_dir: str):
        """
        Args:
            warehouse_dir: 웨어하우스 디렉토리 경로
        """
        self.warehouse_dir = warehouse_dir
        self.tracking_file = os.path.join(warehouse_dir, ".training_status.json")
        self._ensure_dir()
        
    def _ensure_dir(self):
        """웨어하우스 디렉토리가 존재하는지 확인하고 없으면 생성"""
        os.makedirs(self.warehouse_dir, exist_ok=True)
    
    def _load_status(self) -> Dict:
        """학습 상태 파일 로드"""
        if not os.path.exists(self.tracking_file):
            return {
                "processed_files": {},
                "processed_releases": [],
                "last_training_date": None,
                "training_history": []
            }
        
        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 파일이 손상된 경우 초기 상태로 리셋
            return {
                "processed_files": {},
                "processed_releases": [],
                "last_training_date": None,
                "training_history": []
            }
    
    def _save_status(self, status: Dict):
        """학습 상태 파일 저장"""
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
    
    def is_file_processed(self, file_path: str) -> bool:
        """
        파일이 이미 처리되었는지 확인
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            처리되었다면 True, 아니면 False
        """
        status = self._load_status()
        normalized_path = os.path.abspath(file_path)
        return normalized_path in status.get("processed_files", {})
    
    def mark_file_processed(self, file_path: str, release: str, records: Dict[str, int]):
        """
        파일이 처리되었음을 표시
        
        Args:
            file_path: 처리된 파일 경로
            release: 릴리스 문자열 (예: "2024_01")
            records: 처리된 레코드 수 정보 (예: {"total": 1000, "metrics": 800, "star": 200})
        """
        status = self._load_status()
        normalized_path = os.path.abspath(file_path)
        
        # 파일 정보 저장
        status["processed_files"][normalized_path] = {
            "release": release,
            "records": records,
            "processed_at": datetime.now().isoformat(),
            "file_name": os.path.basename(file_path)
        }
        
        # 릴리스 목록에 추가 (중복 방지)
        if release not in status.get("processed_releases", []):
            status["processed_releases"] = sorted(
                status.get("processed_releases", []) + [release]
            )
        
        # 마지막 학습 날짜 업데이트
        status["last_training_date"] = datetime.now().isoformat()
        
        # 학습 히스토리에 추가
        history_entry = {
            "file_path": normalized_path,
            "file_name": os.path.basename(file_path),
            "release": release,
            "records": records,
            "processed_at": datetime.now().isoformat()
        }
        status["training_history"] = status.get("training_history", [])
        status["training_history"].append(history_entry)
        
        # 최근 50개만 유지
        if len(status["training_history"]) > 50:
            status["training_history"] = status["training_history"][-50:]
        
        self._save_status(status)
    
    def is_ai_training_complete(self, release: str) -> bool:
        """
        특정 릴리스의 AI 학습이 완료되었는지 확인
        
        Args:
            release: 릴리스 문자열
            
        Returns:
            완료되었으면 True, 아니면 False
        """
        status = self._load_status()
        ai_complete = status.get("ai_training_complete", {})
        return ai_complete.get(release, False)
    
    def mark_ai_training_complete(self, release: str, predictions: int, metrics: Optional[Dict] = None):
        """
        특정 릴리스의 AI 학습 완료 표시
        
        Args:
            release: 릴리스 문자열
            predictions: 생성된 예측 수
            metrics: 평가 메트릭 (선택적)
        """
        status = self._load_status()
        
        if "ai_training_complete" not in status:
            status["ai_training_complete"] = {}
        
        status["ai_training_complete"][release] = {
            "completed_at": datetime.now().isoformat(),
            "predictions": predictions,
            "metrics": metrics or {}
        }
        
        self._save_status(status)
    
    def get_incomplete_ai_trainings(self, releases: List[str]) -> List[str]:
        """
        AI 학습이 완료되지 않은 릴리스 목록 반환
        
        Args:
            releases: 확인할 릴리스 목록
            
        Returns:
            완료되지 않은 릴리스 목록
        """
        incomplete = []
        for release in releases:
            if not self.is_ai_training_complete(release):
                incomplete.append(release)
        return incomplete
    
    def get_processed_releases(self) -> List[str]:
        """처리된 릴리스 목록 반환"""
        status = self._load_status()
        return sorted(status.get("processed_releases", []))
    
    def get_processed_files(self) -> Dict[str, Dict]:
        """처리된 파일 정보 반환"""
        status = self._load_status()
        return status.get("processed_files", {})
    
    def reset_training_status(self):
        """모든 학습 상태 초기화"""
        status = {
            "processed_files": {},
            "processed_releases": [],
            "last_training_date": None,
            "training_history": []
        }
        self._save_status(status)
    
    def get_recent_training(self, limit: int = 10) -> List[Dict]:
        """최근 학습 기록 반환"""
        status = self._load_status()
        history = status.get("training_history", [])
        return history[-limit:] if history else []


class DataFileManager:
    """
    데이터 파일 관리 유틸리티 클래스.
    
    기능:
    - ZIP 파일 및 디렉터리 검색
    - 날짜(릴리스) 추출 및 정렬
    """
    
    @staticmethod
    def find_zip_files(data_dir: str) -> List[Dict[str, str]]:
        """
        데이터 디렉토리에서 ZIP 파일 찾기
        
        Args:
            data_dir: 데이터 디렉토리 경로
            
        Returns:
            [{"path": "...", "release": "2024_01", "filename": "..."}] 형태의 리스트
        """
        if not os.path.exists(data_dir):
            return []
        
        zip_files = []
        data_path = Path(data_dir)
        
        for zip_file in data_path.glob("*.zip"):
            # 릴리스 추출 (extract.py의 _infer_release_from_zip과 동일한 로직)
            release = DataFileManager._infer_release_from_filename(zip_file.name)
            
            zip_files.append({
                "path": str(zip_file.resolve()),
                "release": release,
                "filename": zip_file.name,
                "mtime": zip_file.stat().st_mtime
            })
        
        # 날짜순으로 정렬 (release 기준, 그 다음 mtime)
        zip_files.sort(key=lambda x: (x["release"], x["mtime"]))
        
        return zip_files

    @staticmethod
    def find_input_items(data_dir: str) -> List[Dict[str, str]]:
        """
        데이터 디렉토리에서 처리 대상(최상위 ZIP 또는 디렉터리)을 찾는다.
        반환: [{"path","release","filename","mtime","type"}] (type: zip|dir)
        """
        if not os.path.exists(data_dir):
            return []
        items: List[Dict[str, str]] = []
        data_path = Path(data_dir)
        # ZIP
        for zip_file in data_path.glob("*.zip"):
            release = DataFileManager._infer_release_from_filename(zip_file.name)
            items.append({
                "path": str(zip_file.resolve()),
                "release": release,
                "filename": zip_file.name,
                "mtime": zip_file.stat().st_mtime,
                "type": "zip",
            })
        # Directories (1-depth)
        for d in data_path.iterdir():
            if d.is_dir():
                release = DataFileManager._infer_release_from_filename(d.name)
                items.append({
                    "path": str(d.resolve()),
                    "release": release,
                    "filename": d.name,
                    "mtime": d.stat().st_mtime,
                    "type": "dir",
                })
        # 정렬: release, mtime
        items.sort(key=lambda x: (x["release"], x["mtime"]))
        return items
    
    @staticmethod
    def _infer_release_from_filename(filename: str) -> str:
        """
        파일명에서 릴리스 추출 (YYYY_MM 형식)
        
        Args:
            filename: 파일명 (예: "hospitals_01_2024.zip")
            
        Returns:
            릴리스 문자열 (예: "2024_01") 또는 "unknown"
        """
        import re
        
        # YYYY[_-]MM 패턴 우선 시도
        m = re.search(r"(20\d{2})[._-]?(0[1-9]|1[0-2])", filename)
        if m:
            year, month = m.group(1), m.group(2)
            return f"{year}_{month}"
        
        # MM[_-]YYYY 패턴 시도
        m = re.search(r"(0[1-9]|1[0-2])[._-]?(20\d{2})", filename)
        if m:
            month, year = m.group(1), m.group(2)
            return f"{year}_{month}"
        
        return "unknown"
    
    @staticmethod
    def get_date_range(zip_files: List[Dict[str, str]]) -> Dict[str, Optional[str]]:
        """
        ZIP 파일 목록에서 날짜 범위 추출
        
        Args:
            zip_files: find_zip_files()의 반환값
            
        Returns:
            {"earliest": "2024_01", "latest": "2024_12"} 형태의 딕셔너리
        """
        if not zip_files:
            return {"earliest": None, "latest": None}
        
        releases = [f["release"] for f in zip_files if f["release"] != "unknown"]
        
        if not releases:
            return {"earliest": None, "latest": None}
        
        return {
            "earliest": min(releases),
            "latest": max(releases)
        }

