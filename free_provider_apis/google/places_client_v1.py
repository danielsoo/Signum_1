# free_provider_apis/google/places_client_v1.py
# Minimal Google Places (New, v1) client + Feature Flags + Usage tracking
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import requests

# 절대 임포트(패키지) → 실패 시 로컬 모듈 폴백
try:
    import free_provider_apis.google.usage_tracker as ut
    import free_provider_apis.google.feature_flags as ff
except Exception:
    import usage_tracker as ut
    import feature_flags as ff

UsageTracker = ut.UsageTracker
is_on        = ff.is_on

PLACES_BASE = "https://places.googleapis.com/v1"

# Enterprise로 분류되는 대표 필드들
ENTERPRISE_FIELDS = {
    "rating", "userRatingCount", "reviews",
    "nationalPhoneNumber", "internationalPhoneNumber", "websiteUri",
    "photos",
}

# 기능명 ↔ 필드 매핑(엔터프라이즈)
FEATURE_TO_FIELDS = {
    "rating": {"rating", "userRatingCount"},
    "reviews": {"reviews"},
    "photos_meta": {"photos"},
    "phone": {"nationalPhoneNumber", "internationalPhoneNumber"},
    "website": {"websiteUri"},
}

class PlacesV1Client:
    def __init__(self, api_key: Optional[str] = None,
                 allow_enterprise: bool = False,
                 tracker: Optional[UsageTracker] = None,
                 strict: bool = True) -> None:
        key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_MAPS_API_KEY is required")
        self.api_key: str = key
        self.allow_enterprise = allow_enterprise
        self.strict = strict  # OFF: 자동 필터, ON: 예외
        self.session = requests.Session()
        self.usage = tracker or UsageTracker()

    def _headers(self, field_mask: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

    # -------- Text Search (Pro) --------
    def search_text(self, text_query: str,
                    location_bias: Optional[Dict[str, Any]] = None,
                    fields: Optional[List[str]] = None,
                    timeout: int = 20) -> Dict[str, Any]:
        # 기능 스위치
        if not is_on("text_search"):
            if self.strict:
                raise RuntimeError("Feature 'text_search' is disabled")
            return {"places": []}

        url = f"{PLACES_BASE}/places:searchText"
        fields = fields or ["places.id", "places.displayName", "places.formattedAddress"]
        field_mask = ",".join(fields)

        # 카운트
        self.usage.inc("text_search_pro")

        body: Dict[str, Any] = {"textQuery": text_query}
        if location_bias:
            body.update(location_bias)
        resp = self.session.post(url, headers=self._headers(field_mask), json=body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    # -------- Place Details --------
    def place_details(self, place_id: str,
                      fields: Optional[List[str]] = None,
                      timeout: int = 20) -> Dict[str, Any]:
        # 기능 스위치
        if not is_on("details_essentials"):
            if self.strict:
                raise RuntimeError("Feature 'details_essentials' is disabled")
            return {}

        url = f"{PLACES_BASE}/places/{place_id}"
        # 기본: Essentials
        fields = fields or ["id", "displayName", "formattedAddress", "location", "shortFormattedAddress"]

        # 1) 스위치 기반 필드 검증/필터링
        requested = {f.split(".")[-1] for f in fields}
        blocked = []
        for feat, fset in FEATURE_TO_FIELDS.items():
            if requested & fset and not is_on(feat):
                blocked.extend(sorted(requested & fset))
        if blocked:
            if self.strict:
                raise RuntimeError(f"Disabled features in field mask: {', '.join(blocked)}")
            # 느슨 모드: 막힌 필드 제거
            fields = [f for f in fields if (f.split(".")[-1] not in blocked)]

        # 2) 과금 구간 집계
        last_tokens = {f.split(".")[-1] for f in fields}
        enterprise = any(tok in ENTERPRISE_FIELDS for tok in last_tokens)
        if enterprise:
            if not self.allow_enterprise:
                if self.strict:
                    raise RuntimeError("Enterprise fields requested but allow_enterprise=False")
                # 느슨 모드: 엔터프라이즈 필드 제거 → Essentials
                fields = [f for f in fields if (f.split(".")[-1] not in ENTERPRISE_FIELDS)]
                self.usage.inc("place_details_essentials")
            else:
                self.usage.inc("place_details_enterprise")
        else:
            self.usage.inc("place_details_essentials")

        field_mask = ",".join(fields)
        resp = self.session.get(url, headers=self._headers(field_mask), timeout=timeout)
        resp.raise_for_status()
        return resp.json()
