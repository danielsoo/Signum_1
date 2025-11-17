# free_provider_apis/government/clients_free.py
# Free clients for public healthcare provider data sources (NPPES, NIH ClinicalTables, CMS PDC).
# All comments are in English.

import re
from functools import lru_cache
from typing import Dict, List, Optional, Any

from ..common.config import CONFIG  # central configuration (timeouts, limits, endpoints)
from .http_utils import HttpClient
from .rate_limiter import CompositeLimiter


# -----------------------------
# Small helpers
# -----------------------------
def _normalize_ccns(raw_vals, max_len: int = 50) -> List[str]:
    """
    Extract valid 6-digit numeric CCNs from mixed inputs, dedupe, cap to max_len.
    """
    seen = set()
    out: List[str] = []
    for v in (raw_vals or []):
        s = ",".join(v) if isinstance(v, (list, tuple)) else str(v)
        for ccn in re.findall(r"\b\d{6}\b", s):
            if ccn not in seen:
                seen.add(ccn)
                out.append(ccn)
                if len(out) >= max_len:
                    return out
    return out


def _normalize_terms(t: str) -> str:
    """Trim and normalize input string."""
    return (t or "").strip()


def _tokenize(t: str) -> List[str]:
    """
    Tokenize input string by non-alphanumeric delimiters.
    Only keep tokens with length >= 3 to avoid noise.
    """
    return [tok for tok in re.split(r"[^a-zA-Z0-9]+", (t or "")) if len(tok) >= 3]


# -----------------------------
# NPPES client
# -----------------------------
class NPPESClient:
    """
    Client wrapper for NPPES (National Plan & Provider Enumeration System).
    Uses the public CMS NPI Registry API.
    Docs: https://npiregistry.cms.hhs.gov/api-page
    """

    BASE_URL = (CONFIG.get("nppes") or {}).get("base_url", "https://npiregistry.cms.hhs.gov/api/")
    VERSION = (CONFIG.get("nppes") or {}).get("version", "2.1")

    def __init__(self) -> None:
        self.http = HttpClient()

        # Limits from CONFIG with safe fallbacks
        lim = (CONFIG.get("limits") or {}).get("nppes") or {}
        rps = float(lim.get("rps", 3.0))
        bucket = int(lim.get("bucket", 10))
        daily = int(lim.get("daily", 5000))
        self.limiter = CompositeLimiter(rps=rps, bucket=bucket, daily_quota=daily)

    def search(
        self,
        taxonomy_description: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        number: Optional[str] = None,            # NPI number (10 digits)
        postal_code: Optional[str] = None,       # ZIP or ZIP+4 (digits only is OK)
        enumeration_type: Optional[str] = None,  # "NPI-1" or "NPI-2"
        limit: int = 3,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Perform a provider search on NPPES.
        """
        self.limiter.acquire()

        params: Dict[str, Any] = {
            "version": self.VERSION,
            "limit": max(1, min(limit, 200)),
        }
        if skip:
            params["skip"] = max(0, int(skip))
        if taxonomy_description:
            params["taxonomy_description"] = taxonomy_description
        if state:
            params["state"] = state
        if city:
            params["city"] = city
        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name
        if organization_name:
            params["organization_name"] = organization_name
        if number:
            params["number"] = number
        if postal_code:
            params["postal_code"] = postal_code
        if enumeration_type in {"NPI-1", "NPI-2"}:
            params["enumeration_type"] = enumeration_type

        resp = self.http.get(self.BASE_URL, params=params)
        return self.http.safe_json(resp)

    @staticmethod
    def normalize(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize NPPES response into a richer, consistent schema.
        """
        if not raw or "results" not in raw:
            return []

        out: List[Dict[str, Any]] = []

        for r in raw["results"]:
            npi: Optional[str] = r.get("number")
            enumeration_type: Optional[str] = r.get("enumeration_type")  # "NPI-1" or "NPI-2"

            basic: Dict[str, Any] = r.get("basic") or {}
            taxonomies: List[Dict[str, Any]] = r.get("taxonomies") or []
            addresses: List[Dict[str, Any]] = r.get("addresses") or []
            identifiers: List[Dict[str, Any]] = r.get("identifiers") or []
            endpoints: List[Dict[str, Any]] = r.get("endpoints") or []

            # names / status / dates
            first = basic.get("first_name")
            middle = basic.get("middle_name")
            last = basic.get("last_name")
            org_name = basic.get("organization_name")
            person_name = " ".join([p for p in [first, middle, last] if p]).strip()
            display_name = person_name if person_name else (org_name or None)

            credential = basic.get("credential")
            status = basic.get("status")
            enumeration_date = basic.get("enumeration_date")
            last_updated = basic.get("last_updated")

            # authorized official (mostly for NPI-2)
            auth = {
                "name_prefix": basic.get("authorized_official_name_prefix"),
                "first_name": basic.get("authorized_official_first_name"),
                "middle_name": basic.get("authorized_official_middle_name"),
                "last_name": basic.get("authorized_official_last_name"),
                "title_or_position": basic.get("authorized_official_title_or_position"),
                "telephone_number": basic.get("authorized_official_telephone_number"),
            }
            if not any(auth.values()):
                auth = None

            # addresses
            def _addr(a: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "address_purpose": a.get("address_purpose"),
                    "address_type": a.get("address_type"),
                    "address_1": a.get("address_1"),
                    "address_2": a.get("address_2"),
                    "city": a.get("city"),
                    "state": a.get("state"),
                    "postal_code": a.get("postal_code"),
                    "country_code": a.get("country_code"),
                    "country_name": a.get("country_name"),
                    "telephone_number": a.get("telephone_number"),
                    "fax_number": a.get("fax_number"),
                }

            practice_addresses = [_addr(a) for a in addresses if a.get("address_purpose") == "LOCATION"]
            mailing_addresses  = [_addr(a) for a in addresses if a.get("address_purpose") == "MAILING"]

            # phones/faxes dedupe
            def _dedupe(seq: List[str]) -> List[str]:
                seen = set()
                out_list: List[str] = []
                for s in seq:
                    if s and s not in seen:
                        seen.add(s)
                        out_list.append(s)
                return out_list

            def _collect_str_values(addr_list: List[Dict[str, Any]], key: str) -> List[str]:
                out_vals: List[str] = []
                for a in addr_list:
                    v = a.get(key)
                    if isinstance(v, str) and v.strip():
                        out_vals.append(v)
                return out_vals

            phones = _dedupe(_collect_str_values(addresses, "telephone_number"))
            faxes  = _dedupe(_collect_str_values(addresses, "fax_number"))

            # taxonomies
            primary_tax: Optional[Dict[str, Any]] = None
            for t in taxonomies:
                if t.get("primary"):
                    primary_tax = t
                    break
            if not primary_tax and taxonomies:
                primary_tax = taxonomies[0]

            tax_list = [{
                "code": t.get("code"),
                "desc": t.get("desc"),
                "primary": t.get("primary"),
                "state": t.get("state"),
                "license": t.get("license"),
            } for t in taxonomies]

            # identifiers
            ident_list = [{
                "code": i.get("code"),
                "desc": i.get("desc"),
                "issuer": i.get("issuer"),
                "identifier": i.get("identifier"),
                "state": i.get("state"),
            } for i in identifiers]

            # endpoints
            ep_list = [{
                "endpoint": ep.get("endpoint"),
                "endpoint_type": ep.get("endpointType"),
                "endpoint_description": ep.get("endpointDescription"),
                "use": ep.get("use"),
                "content_type": ep.get("contentType"),
                "affiliation": ep.get("affiliation"),
                "address": ep.get("address"),
            } for ep in endpoints]

            out.append({
                "source": "NPPES",
                "npi": npi,
                "enumeration_type": enumeration_type,
                "status": status,
                "enumeration_date": enumeration_date,
                "last_updated": last_updated,
                "name": display_name,
                "individual_name": {
                    "first_name": first,
                    "middle_name": middle,
                    "last_name": last,
                } if person_name else None,
                "organization_name": org_name if org_name else None,
                "credential": credential,
                "authorized_official": auth,
                "primary_taxonomy": {
                    "code": (primary_tax or {}).get("code"),
                    "desc": (primary_tax or {}).get("desc"),
                    "state": (primary_tax or {}).get("state"),
                    "license": (primary_tax or {}).get("license"),
                } if primary_tax else None,
                "taxonomies": tax_list,
                "practice_addresses": practice_addresses,
                "mailing_addresses": mailing_addresses,
                "phones": phones,
                "faxes": faxes,
                "identifiers": ident_list,
                "endpoints": ep_list,
            })

        return out


# -----------------------------
# CMS Provider Data Catalog (Affiliations + Hospital Quality)
# -----------------------------
class CMSPDCClient:
    """
    Lightweight client for the CMS Provider Data Catalog (PDC).

    Features:
      - Fetch hospital affiliations for a given NPI (Doctors & Clinicians Facility Affiliation dataset)
      - Fetch hospital quality/ratings for given CCNs (Hospital General Information dataset)
    Notes:
      - Dataset URLs are set via CONFIG["cms_pdc"]
      - Safe fallback: returns empty results when CONFIG or endpoint is missing
    """

    def __init__(self):
        self.http = HttpClient()

        pdc_cfg = (CONFIG.get("cms_pdc") or {})
        self.url_doctors = pdc_cfg.get("doctors_affiliations_url") or None
        self.url_hospitals = pdc_cfg.get("hospitals_quality_url") or None

        # Rate limit from CONFIG
        lim = (CONFIG.get("limits") or {}).get("cms") or {}
        rps = float(lim.get("rps", 5.0))
        bucket = int(lim.get("bucket", 5))
        daily = int(lim.get("daily", 5000))
        self.limiter = CompositeLimiter(rps=rps, bucket=bucket, daily_quota=daily)

    # ---------- helpers ----------
    def _extract_affils(self, record: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
        """
        Extract CCNs and hospital names from a single record. CCNs are prioritized.
        """
        out: List[Dict[str, Optional[str]]] = []

        # 1) CCN candidates from various fields
        ccn_candidates: List[str] = []
        for k in (
            "facility_affiliations_certification_number",
            "affiliated_hospital_ccns",
            "facility_type_certification_number",
            "ccn",
        ):
            v = record.get(k)
            if v:
                if isinstance(v, (list, tuple)):
                    ccn_candidates.extend(map(str, v))
                else:
                    ccn_candidates.append(str(v))

        # 2) Valid CCNs (6-digit) only, deduped and capped
        ccns = _normalize_ccns(ccn_candidates, max_len=50)

        # 3) Optional hospital names (may be missing)
        name_blob = (
            record.get("hospital_affiliation_names")
            or record.get("hospital_affiliations")
            or record.get("affiliations")
            or ""
        )
        names: List[str] = []
        if isinstance(name_blob, str) and name_blob.strip():
            names = [x.strip() for x in name_blob.split(";") if x.strip()]

        # 4) Prefer CCNs; keep name=None for later enrichment
        for ccn in ccns:
            out.append({"ccn": ccn, "hospital_name": None})

        # 5) Names without CCN (keep for display; ccn=None)
        for nm in names:
            out.append({"ccn": None, "hospital_name": nm})

        return out

    # ---------- public ----------
    def get_hospital_affiliations_by_npi(self, npi: str) -> List[Dict[str, Optional[str]]]:
        """
        Return hospitals associated with NPI.

        Robust behavior:
          - tries multiple NPI column names: ["npi", "clinician_npi", "npi_number", "provider_npi"]
          - tries multiple filter styles:
              direct key      → {col: value}
              filters-style   → {"filters[col]": value}
              $where quoted   → {"$where": f"{col}='<value>'"}
              $where numeric  → {"$where": f"{col}=<value>"}
          - supports pagination styles: "offset", "$offset", "page"
          - stops on repeated pages or after a max page cap to avoid infinite loops
        """
        if not self.url_doctors or not npi:
            return []

        try:
            all_rows: List[Dict[str, Optional[str]]] = []
            limit = 50
            max_pages = 20  # hard cap per (col, style, pagekey)

            # candidate NPI column names
            npi_cols = ["npi", "clinician_npi", "npi_number", "provider_npi"]

            # filter param styles
            def _p_direct(col, val):     # ?npi=1003000126
                return {col: val}

            def _p_filters(col, val):    # ?filters[npi]=1003000126
                return {f"filters[{col}]": val}

            def _p_where_q(col, val):    # ?$where=npi='1003000126'
                return {"$where": f"{col}='{val}'"}

            def _p_where_nq(col, val):   # ?$where=npi=1003000126
                return {"$where": f"{col}={val}"}

            filter_styles = [_p_direct, _p_filters, _p_where_q, _p_where_nq]
            page_keys = ["offset", "$offset", "page"]

            found_any = False

            for col in npi_cols:
                if found_any:
                    break
                for fstyle in filter_styles:
                    if found_any:
                        break
                    for pkey in page_keys:
                        page = 0
                        offset = 0
                        pages_seen = set()
                        local_rows: List[Dict[str, Optional[str]]] = []

                        while True:
                            self.limiter.acquire()

                            # build params
                            params = {"limit": limit}
                            params.update(fstyle(col, npi))

                            # pagination
                            if pkey == "page":
                                params["page"] = page + 1  # 1-based
                            elif pkey == "$offset":
                                params["$offset"] = offset
                            else:
                                params["offset"] = offset

                            data = self.http.safe_json(self.http.get(self.url_doctors, params=params)) or {}
                            recs = data.get("records") or data.get("data") or data.get("results") or []

                            # detect repeated page signature
                            head = recs[0] if recs else {}
                            sig = (
                                col, fstyle.__name__, pkey,
                                page, offset, len(recs),
                                head.get("npi") or head.get("clinician_npi") or head.get("npi_number") or head.get("provider_npi"),
                                head.get("facility_affiliations_certification_number") or head.get("ccn"),
                            )
                            if sig in pages_seen:
                                break
                            pages_seen.add(sig)

                            if recs:
                                found_any = True
                                # FIX: iterate each record (previous bug passed the whole list)
                                for rec in recs:
                                    local_rows.extend(self._extract_affils(rec))

                            # next page
                            page += 1
                            offset += limit
                            if len(recs) < limit:
                                break
                            if page >= max_pages:
                                break

                        if local_rows:
                            # de-duplicate within this working tuple
                            seen = set()
                            deduped: List[Dict[str, Optional[str]]] = []
                            for x in local_rows:
                                key = (x.get("ccn"), x.get("hospital_name"))
                                if key in seen:
                                    continue
                                seen.add(key)
                                deduped.append(x)
                            all_rows.extend(deduped)
                            break  # stop after first working (col, style, pagekey)

            # final de-duplication
            seen2 = set()
            out: List[Dict[str, Optional[str]]] = []
            for x in all_rows:
                key = (x.get("ccn"), x.get("hospital_name"))
                if key in seen2:
                    continue
                seen2.add(key)
                out.append(x)
            return out

        except Exception:
            return []

    @lru_cache(maxsize=2048)
    def get_hospital_quality_by_ccns(self, ccns: tuple) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Batch fetch hospital info for a list of CCNs via SoQL IN.
        Args:
          ccns: tuple of 6-digit CCNs (hashable for lru_cache)
        Returns:
          dict[ccn] -> { provider_ccn, hospital_name, overall_rating }
        """
        out: Dict[str, Dict[str, Optional[str]]] = {}
        if not self.url_hospitals or not ccns:
            return out

        # keep only valid 6-digit numeric CCNs
        ccns_list = [c for c in ccns if isinstance(c, str) and re.fullmatch(r"\d{6}", c)]
        if not ccns_list:
            return out

        BATCH = 40  # query in chunks
        for i in range(0, len(ccns_list), BATCH):
            chunk = ccns_list[i:i + BATCH]
            where = "provider_ccn in ({})".format(",".join([f'"{c}"' for c in chunk]))
            params = {
                "$select": "provider_ccn,hospital_name,overall_rating",
                "$where": where,
                "$limit": len(chunk),
            }
            try:
                data = self.http.safe_json(self.http.get(self.url_hospitals, params=params)) or {}
                rows = data.get("data", []) or data.get("records") or data.get("results") or []
                for r in rows:
                    ccn = (r.get("provider_ccn") or "").strip()
                    if re.fullmatch(r"\d{6}", ccn or ""):
                        rating = r.get("overall_rating")
                        if rating in (None, "", "Not Available", "Not Applicable"):
                            rating = r.get("hospital_overall_rating")  # fallback key
                        out[ccn] = {
                            "provider_ccn": ccn,
                            "hospital_name": r.get("hospital_name"),
                            "overall_rating": rating
                        }
            except Exception:
                # be resilient: skip this chunk on error
                continue

        return out
