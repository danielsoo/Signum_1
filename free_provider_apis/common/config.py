# config.py
import os

CONFIG = {
    "http": {
        "timeout": int(os.getenv("HTTP_TIMEOUT", "25")),
        "max_retries": int(os.getenv("HTTP_MAX_RETRIES", "2")),  # 1 try + 2 retries total attempts = 3
        "backoff_base": float(os.getenv("HTTP_BACKOFF_BASE", "1.5")),
        "backoff_factor": float(os.getenv("HTTP_BACKOFF_FACTOR", "2.0")),
        "jitter": float(os.getenv("HTTP_JITTER", "0.4")),
        "user_agent": os.getenv("HTTP_USER_AGENT", "Signum-FreeProviderSmoke/1.0 (contact@example.com)"),
    },

    # Per-source quota/rate (conservative defaults; adjust if needed)
    "limits": {
        "nppes":   {"rps": float(os.getenv("NPPES_RPS", "5")),  "bucket": int(os.getenv("NPPES_BUCKET", "5")),  "daily": int(os.getenv("NPPES_DAILY", "1000"))},
        "ctss":    {"rps": float(os.getenv("CTSS_RPS", "10")),  "bucket": int(os.getenv("CTSS_BUCKET", "10")),  "daily": int(os.getenv("CTSS_DAILY", "1000"))},
        "cms":     {"rps": float(os.getenv("CMS_RPS", "5")),    "bucket": int(os.getenv("CMS_BUCKET", "5")),    "daily": int(os.getenv("CMS_DAILY", "5000"))},
    },

    # Endpoints & auth
    "nppes": {
        "base_url": "https://npiregistry.cms.hhs.gov/api/",
        "version": "2.1",
    },
    "ctss": {
        "base_url": "https://clinicaltables.nlm.nih.gov/api/npi_idv/v3/search",
        # CTSS는 키 불필요. (NCBI key는 eUtils 계열에서 사용)
    },
    "cms": {
        "base_url": "https://data.cms.gov/resource",
        "app_token": os.getenv("CMS_APP_TOKEN", "4ehSDZu0WLkTP1nJX7PTVTBSxfKfRHH6"),
        # 원하는 공개 데이터셋 ID 지정(예: Provider of Services 등). 비워두면 smoke에서 CMS는 건너뜀.
        "dataset_id": os.getenv("CMS_DATASET_ID", ""),
    },

    "cms_pdc": {
        # Doctors & Clinicians Facility Affiliation (NPI -> hospital CCN)
        "doctors_affiliations_url": "https://data.cms.gov/provider-data/api/1/datastore/query/27ea-46a8/0",

        # Hospital General Information (CCN -> name, overall rating, etc.)
        "hospitals_quality_url": "https://data.cms.gov/provider-data/api/1/datastore/query/hospital-general-information/0"
    }
}

CONFIG.update({
    "google_maps": {
        "api_key": os.getenv("GOOGLE_MAPS_API_KEY", ""),  # <-- 여기에 키 or env
    },
    "limits": {
        "google_maps": {"rps": 8, "bucket": 8, "daily": 10000},  # 필요시 조정
        **(CONFIG.get("limits") or {})
    }
})