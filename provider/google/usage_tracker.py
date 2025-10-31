# free_provider_apis/google/usage_tracker.py
from __future__ import annotations
import json, os, sys, time
from typing import Dict, Optional
from pathlib import Path

__all__ = ["UsageTracker", "DEFAULT_LIMITS"]

# SKU별 월 무료 한도(요약)
DEFAULT_LIMITS: Dict[str, int] = {
    "text_search_pro": 5_000,              # Places API Text Search Pro
    "place_details_essentials": 10_000,    # Place Details Essentials
    "place_details_enterprise": 1_000,     # Place Details Enterprise (rating/reviews/phone/website/photos)
    "place_details_photos": 1_000,         # Photos /media (프록시에서 증가 권장)
}

# 모듈(google 폴더) 기준 기본 경로
MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_USAGE_PATH = MODULE_DIR / ".usage_counters.json"

class UsageTracker:
    def __init__(self, path: Optional[str] = None, limits: Optional[Dict[str,int]] = None) -> None:
        """
        우선순위: 1) 인자 path 2) 환경변수 FREE_USAGE_PATH 3) google 폴더의 .usage_counters.json
        - 절대경로로 정규화
        - 부모 폴더 없으면 자동 생성
        """
        raw = path or os.getenv("FREE_USAGE_PATH") or str(DEFAULT_USAGE_PATH)
        raw = os.path.expanduser(raw)
        self.path = os.path.abspath(raw)

        self.limits = dict(DEFAULT_LIMITS)
        if limits:
            self.limits.update(limits)
        self.data = self._load()

    @staticmethod
    def _month_key() -> str:
        return time.strftime("%Y-%m")

    def _load(self) -> Dict[str, Dict[str, int]]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                # 파일이 깨졌거나 권한 이슈면 새로 시작
                pass
        return {}

    def _save(self) -> None:
        # 부모 폴더 자동 생성 (상대경로로 폴더 중첩되어도 안전)
        parent = os.path.dirname(self.path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def inc(self, sku: str, by: int = 1, echo: bool = True) -> int:
        month = self._month_key()
        bucket = self.data.setdefault(month, {})
        bucket[sku] = int(bucket.get(sku, 0)) + by
        self._save()
        used = bucket[sku]
        lim = self.limits.get(sku)
        if echo:
            lim_txt = f"{lim}" if lim is not None else "∞"
            print(f"[GoogleUsage] {sku}: {used} / {lim_txt} (this month)", file=sys.stderr)
        return used

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        month = self._month_key()
        b = self.data.get(month, {})
        out: Dict[str, Dict[str, int]] = {}
        for sku, limit in self.limits.items():
            out[sku] = {"used": int(b.get(sku, 0)), "limit": limit}
        return out
