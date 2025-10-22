# free_provider_apis/google/feature_flags.py

from __future__ import annotations
import os
from typing import Dict

__all__ = ["enable", "disable", "is_on", "all", "set_many", "load_from_env"]

# 기본값: 무료 모드 / 엔터프라이즈(유료 트리거)는 OFF
_DEFAULTS: Dict[str, bool] = {
    "text_search": True,          # 텍스트 검색 on/off
    "details_essentials": True,   # Essentials 세부정보 on/off

    # Enterprise (유료 트리거)
    "rating": False,              # rating, userRatingCount
    "reviews": False,             # reviews
    "photos_meta": False,         # place details 응답의 photos 메타
    "photo_media": False,         # /v1/{photo.name}/media (별도 라우트에서 체크)
    "phone": False,               # nationalPhoneNumber, internationalPhoneNumber
    "website": False,             # websiteUri
}

_FEATURES: Dict[str, bool] = dict(_DEFAULTS)

def enable(name: str) -> None:
    if name not in _FEATURES: raise KeyError(name)
    _FEATURES[name] = True

def disable(name: str) -> None:
    if name not in _FEATURES: raise KeyError(name)
    _FEATURES[name] = False

def is_on(name: str) -> bool:
    return bool(_FEATURES.get(name, False))

def all() -> Dict[str, bool]:
    return dict(_FEATURES)

def set_many(upd: Dict[str, bool]) -> None:
    for k, v in upd.items():
        if k in _FEATURES:
            _FEATURES[k] = bool(v)

def load_from_env(var: str = "FREE_FEATURES") -> None:
    """
    환경변수 예: FREE_FEATURES='rating=on,reviews=off,photos_meta=on'
    """
    s = os.getenv(var, "").strip()
    if not s:
        return
    for pair in s.split(","):
        if "=" not in pair:
            continue
        k, v = [x.strip() for x in pair.split("=", 1)]
        if not k:
            continue
        if k in _FEATURES:
            _FEATURES[k] = (v.lower() in ("1", "on", "true", "yes"))
