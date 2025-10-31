# free_provider_apis/government/clinicaltables_client.py

# Robust ClinicalTables client for NPI search (individuals + organizations)
# - Uses correct param "maxList" (not "count")
# - Uses proper endpoints per index:
#     * Individuals: npi_idv/v3/search
#     * Organizations: npi_org/v1/search
# - Uses proper df/sf per index (name.full vs org_name)
# - Falls back to built-in defaults if CONFIG is missing/incomplete
# - Deduplicates by NPI and returns normalized lightweight rows

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from ..common.config import CONFIG  # optional
except Exception:
    CONFIG = {}  # allow running without external config

from .http_utils import HttpClient
from .rate_limiter import CompositeLimiter


def _normalize_terms(t: str) -> str:
    return (t or "").strip()


def _tokenize(t: str) -> List[str]:
    # split by non-alphanumeric, keep tokens length >= 3
    return [tok for tok in re.split(r"[^a-zA-Z0-9]+", (t or "")) if len(tok) >= 3]


SYNONYM_EXPANSIONS = {
    # Cardiology / Heart
    "cardio": ["cardiology", "cardiologist", "cardiovascular", "cardiovascular disease", "heart doctor", "heart clinic"],
    "cards": ["cardiology", "cardiologist"],
    "cv": ["cardiology", "cardiovascular"],
    "cvd": ["cardiovascular disease"],
    "heart": ["cardiology", "cardiologist", "cardiovascular"],

    # ENT / Otolaryngology
    "ent": ["otolaryngology", "otolaryngologist", "ear nose throat", "ear nose and throat", "throat doctor", "sinus clinic"],
    "orl": ["otolaryngology", "otolaryngologist"],
    "ear": ["otolaryngology", "ear nose throat"],
    "sinus": ["otolaryngology", "ear nose throat"],

    # OB/GYN / Women’s health
    "obgyn": ["obstetrics and gynecology", "obstetrics", "gynecology", "obstetrician", "gynecologist", "women's health"],
    "ob/gyn": ["obstetrics and gynecology", "obstetrics", "gynecology"],
    "ob": ["obstetrics", "obstetrician"],
    "gyn": ["gynecology", "gynecologist"],
    "women": ["obstetrics and gynecology", "women's health"],

    # Dermatology / Skin
    "derm": ["dermatology", "dermatologist", "skin"],
    "skin": ["dermatology", "dermatologist", "skin clinic", "acne clinic", "psoriasis clinic"],

    # Emergency Medicine
    "er": ["emergency medicine", "emergency department"],
    "ed": ["emergency medicine", "emergency department"],
    "em": ["emergency medicine"],

    # Primary Care / Family / Internal
    "pcp": ["primary care", "family medicine", "internal medicine", "general practitioner"],
    "primary": ["primary care", "family medicine", "internal medicine"],
    "family": ["family medicine", "primary care"],
    "fm": ["family medicine"],
    "im": ["internal medicine"],
    "gp": ["general practitioner", "primary care"],

    # Pediatrics
    "peds": ["pediatrics", "pediatrician"],
    "pedi": ["pediatrics", "pediatrician"],
    "pediatric": ["pediatrics", "pediatrician"],

    # Psychiatry / Behavioral
    "psych": ["psychiatry", "psychiatrist", "behavioral health"],
    "psychiatric": ["psychiatry", "psychiatrist"],
    "behavioral": ["behavioral health", "psychiatry", "psychology"],
    "counselor": ["behavioral health", "mental health"],
    "lcsw": ["behavioral health", "clinical social worker"],

    # Neurology
    "neuro": ["neurology", "neurologist"],
    "stroke": ["neurology", "stroke clinic"],

    # Orthopedics / Sports / PM&R
    "ortho": ["orthopedics", "orthopedic surgeon", "sports medicine"],
    "orthopedics": ["orthopedics", "orthopedic surgeon"],
    "sports": ["sports medicine", "orthopedics"],
    "pmr": ["physical medicine and rehabilitation", "physiatry"],
    "pm&r": ["physical medicine and rehabilitation", "physiatry"],
    "physiatry": ["physical medicine and rehabilitation"],

    # Ophthalmology / Optometry
    "ophtho": ["ophthalmology", "ophthalmologist", "eye doctor"],
    "ophthalmology": ["ophthalmology", "ophthalmologist", "eye clinic"],
    "optometry": ["optometry", "optometrist"],

    # Urology
    "uro": ["urology", "urologist"],
    "urologic": ["urology", "urologist"],

    # Gastroenterology
    "gi": ["gastroenterology", "gastroenterologist", "digestive disease"],
    "gastro": ["gastroenterology", "gastroenterologist"],

    # Endocrinology
    "endo": ["endocrinology", "endocrinologist", "diabetes clinic", "thyroid clinic"],
    "diabetes": ["endocrinology", "diabetes clinic"],

    # Hematology / Oncology
    "heme": ["hematology", "hematologist"],
    "onc": ["oncology", "oncologist", "cancer center"],
    "heme/onc": ["hematology", "oncology", "hematology oncology"],

    # Rheumatology
    "rheum": ["rheumatology", "rheumatologist", "arthritis clinic"],

    # Nephrology
    "neph": ["nephrology", "nephrologist", "kidney clinic"],
    "renal": ["nephrology", "nephrologist"],

    # Pulmonology / Allergy / Sleep
    "pulm": ["pulmonology", "pulmonologist", "lung clinic"],
    "pulmonary": ["pulmonology", "pulmonologist"],
    "allergy": ["allergy and immunology", "allergist", "immunology"],
    "immunology": ["allergy and immunology", "immunologist"],
    "sleep": ["sleep medicine", "sleep clinic"],

    # Anesthesiology / Pain
    "anesthesia": ["anesthesiology", "anesthesiologist"],
    "pain": ["pain medicine", "pain management clinic"],

    # Radiology / Imaging
    "rad": ["radiology", "radiologist", "medical imaging"],
    "imaging": ["radiology", "medical imaging", "diagnostic imaging"],

    # Pathology
    "path": ["pathology", "pathologist"],

    # Surgery (and subspecialties)
    "surg": ["surgery", "general surgery", "surgeon"],
    "general surgery": ["surgery", "general surgeon"],
    "vascular": ["vascular surgery", "vascular surgeon"],
    "colorectal": ["colorectal surgery", "colorectal surgeon"],
    "thoracic": ["thoracic surgery", "thoracic surgeon"],
    "plastic": ["plastic surgery", "plastic surgeon"],
    "hand": ["hand surgery", "hand surgeon"],

    # Geriatrics
    "geriatric": ["geriatrics", "geriatric medicine", "geriatrician"],
    "senior": ["geriatrics", "geriatric medicine"],

    # Podiatry / Foot
    "podiatry": ["podiatry", "podiatrist", "foot clinic"],
    "foot": ["podiatry", "podiatrist"],

    # Dental
    "dent": ["dentistry", "dentist", "dental clinic"],
    "ortho-dent": ["orthodontics", "orthodontist"],
    "perio": ["periodontics", "periodontist"],
    "oral": ["oral and maxillofacial surgery", "oral surgeon"],

    # Rehab Therapies
    "pt": ["physical therapy", "physical therapist"],
    "ot": ["occupational therapy", "occupational therapist"],
    "speech": ["speech therapy", "speech-language pathology", "slp"],
    "slp": ["speech-language pathology", "speech therapy"],

    # Pharmacy
    "rx": ["pharmacy", "pharmacist"],
    "pharm": ["pharmacy", "pharmacist"],

    # Infectious Disease
    "id": ["infectious disease", "infectious diseases", "infectious disease specialist"],
    "infectious": ["infectious disease", "infectious diseases"],

    # Urgent / Walk-in / Hospitalist
    "urgent": ["urgent care", "walk-in clinic"],
    "walkin": ["urgent care", "walk-in clinic"],
    "hospitalist": ["hospital medicine", "internal medicine"],
}


class ClinicalTablesClient:
    """
    Query NIH ClinicalTables for NPI (individuals and organizations).
    Docs:
      - Individuals:   https://clinicaltables.nlm.nih.gov/apidoc/npi_idv/v3/doc.html
      - Organizations: https://clinicaltables.nlm.nih.gov/apidoc/npi_org/v1/doc.html
    """

    # Built-in safe defaults (used if CONFIG is missing)
    DEFAULTS = {
        "npi_idv": "https://clinicaltables.nlm.nih.gov/api/npi_idv/v3/search",
        "npi_org": "https://clinicaltables.nlm.nih.gov/api/npi_org/v3/search",
        "default_count": 5,
        "rps": 3.0,
        "bucket": 10,
        "daily_quota": 5000,
    }

    def __init__(
        self,
        rps: Optional[float] = None,
        bucket: Optional[int] = None,
        daily_quota: Optional[int] = None,
        url_idv: Optional[str] = None,
        url_org: Optional[str] = None,
        default_count: Optional[int] = None,
    ):
        cfg = (CONFIG.get("clinicaltables") or {})

        self.url_idv = url_idv or cfg.get("npi_idv") or self.DEFAULTS["npi_idv"]
        self.url_org = url_org or cfg.get("npi_org") or self.DEFAULTS["npi_org"]

        self.default_count = int(default_count or cfg.get("default_count") or self.DEFAULTS["default_count"])

        self.limiter = CompositeLimiter(
            rps or cfg.get("rps") or self.DEFAULTS["rps"],
            bucket or cfg.get("bucket") or self.DEFAULTS["bucket"],
            daily_quota or cfg.get("daily_quota") or self.DEFAULTS["daily_quota"],
        )
        self.http = HttpClient()

    # ---------- low-level helpers ----------
    @staticmethod
    def _validate_payload(payload: Any, url: str) -> Tuple[int, List[List]]:
        """
        Expected schema: [ total, fields, ef, rows ]
        rows can be None -> treat as []
        """
        if not isinstance(payload, list) or len(payload) < 4:
            raise RuntimeError(
                f"Unexpected JSON shape from ClinicalTables ({url}). "
                f"Expected [total, fields, ef, rows], got {type(payload).__name__} with len={len(payload) if isinstance(payload, list) else 'n/a'}."
            )
        total = payload[0] if isinstance(payload[0], int) else 0
        rows = payload[3] or []
        if not isinstance(rows, list):
            rows = []
        return total, rows

    def _hit(
        self,
        url: str,
        terms: str,
        max_list: int,
        offset: int,
        df: str,
        sf: str,
    ) -> Tuple[int, List[List]]:
        self.limiter.acquire(1)
        params = {
            "terms": terms,
            "maxList": max_list,  # IMPORTANT: ClinicalTables uses "maxList"
            "offset": offset,
            "df": df,
            "sf": sf,
        }
        resp = self.http.get(url, params=params)
        payload = self.http.safe_json(resp)
        total, rows = self._validate_payload(payload, url)
        return total, rows

    def _query_both(self, terms: str, count: int, offset: int = 0) -> List[List]:
        """Query organizations + individuals, merge rows (order: org then idv)."""
        if not terms:
            return []
        rows_all: List[List] = []

        # ORG index: uses org_name for display/search
        _, rows_org = self._hit(
            self.url_org,
            terms=terms,
            max_list=count,
            offset=offset,
            df="org_name,NPI,provider_type,addr_practice.full",
            sf="NPI,org_name,provider_type,addr_practice.full",
        )
        rows_all.extend(rows_org or [])

        # IDV index: uses name.full for display/search
        _, rows_idv = self._hit(
            self.url_idv,
            terms=terms,
            max_list=count,
            offset=offset,
            df="name.full,NPI,provider_type,addr_practice.full",
            sf="NPI,name.full,provider_type,addr_practice.full",
        )
        rows_all.extend(rows_idv or [])

        return rows_all

    # ---------- public API ----------
    def search(
        self,
        terms: str,
        count: Optional[int] = None,
        offset: int = 0,
        include_individuals: bool = True,   # kept for parity (currently both queried)
        include_organizations: bool = True, # kept for parity (currently both queried)
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of rows with keys:
          - name
          - npi
          - type
          - practiceAddress
          - source: "clinicaltables"
        """
        max_list = int(count or self.default_count)
        base = _normalize_terms(terms)

        # 1) original terms
        results_rows: List[List] = self._query_both(base, max_list, offset)

        # 2) tokens (single keywords) if nothing found
        if not results_rows:
            for tok in _tokenize(base):
                results_rows = self._query_both(tok, max_list, offset)
                if results_rows:
                    break

        # 3) synonym expansions if still nothing
        if not results_rows:
            expansions: List[str] = []
            for tok in _tokenize(base.lower()):
                expansions.extend(SYNONYM_EXPANSIONS.get(tok, []))
            seen = set()
            uniq_expansions = [e for e in expansions if not (e in seen or seen.add(e))]
            for exp in uniq_expansions:
                results_rows = self._query_both(exp, max_list, offset)
                if results_rows:
                    break

        # Map rows (df order fixed per index) & dedupe by NPI
        out: List[Dict[str, Any]] = []
        seen_npi = set()
        for row in results_rows:
            name = row[0] if len(row) > 0 else None
            npi = str(row[1]) if len(row) > 1 and row[1] is not None else None
            typ = row[2] if len(row) > 2 else None
            addr = row[3] if len(row) > 3 else None
            if not npi or npi in seen_npi:
                continue
            seen_npi.add(npi)
            out.append(
                {
                    "name": name,
                    "npi": npi,
                    "type": typ,
                    "practiceAddress": addr,
                    "source": "clinicaltables",
                }
            )
            if len(out) >= max_list:
                break

        return out
