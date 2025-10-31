# free_provider_apis/government/cli.py
# Interactive CLI for NPPES and NIH ClinicalTables.
# Modes:
#   - compact  : concise summary
#   - detailed : RAW JSON dump (all fields)
#   - enriched : pretty summary + CMS hospital affiliations and ratings
# All code, comments, and messages are in English.

from pathlib import Path
from typing import List

# .env 로드 (repo root: signum/)
try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(ROOT / ".env")
except Exception:
    pass

from typing import Any, Dict, List, Optional
import json
import re  # used in enriched printing

# Import handling: works both as module (-m) and as script
try:
    from .clients_free import NPPESClient, CMSPDCClient
    from .clinicaltables_client import ClinicalTablesClient
except Exception:
    from clients_free import NPPESClient, CMSPDCClient  # type: ignore
    from clinicaltables_client import ClinicalTablesClient  # type: ignore


# =============================
# IO helpers
# =============================
def ask(prompt: str, default: str = "") -> str:
    """Prompt user for input and return as string."""
    s = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return s if s else default


def ask_int(prompt: str, default: int) -> int:
    """Prompt the user for integer input with validation."""
    while True:
        s = input(f"{prompt} [{default}]: ").strip()
        if not s:
            return default
        try:
            val = int(s)
            if val > 0:
                return val
            print("Please enter a positive integer.")
        except ValueError:
            print("Invalid number, please enter an integer.")


def ask_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    """Ask user to select one of the given choices."""
    if not choices:
        raise ValueError("Choices list cannot be empty.")
    if default is None:
        default = choices[0]
    rendered = " / ".join([f"[{c}]" if c == default else c for c in choices])
    while True:
        s = input(f"{prompt}: {rendered} ").strip().lower()
        if not s:
            return default
        if s in choices:
            return s
        print(f"Please choose one of: {', '.join(choices)}")


def print_divider() -> None:
    """Print divider for readability."""
    print("-" * 80)


def format_address(addr: Dict[str, Any]) -> str:
    """Format address dictionary into a readable line."""
    parts = [addr.get("address_1"), addr.get("address_2"), addr.get("city"), addr.get("state"), addr.get("postal_code")]
    return " ".join([p for p in parts if p])


# =============================
# NPPES output
# =============================
def print_nppes_compact(items: List[Dict[str, Any]]) -> None:
    """Compact, human-friendly format."""
    if not items:
        print("No results found.")
        return
    for i, it in enumerate(items, 1):
        primary = it.get("primary_taxonomy") or {}
        prac = it.get("practice_addresses") or []
        phones = it.get("phones") or []
        print(f"[{i}] NPI={it.get('npi')}  TYPE={it.get('enumeration_type')}  STATUS={it.get('status')}")
        print(f"    NAME: {it.get('name')}")
        if primary:
            print(f"    PRIMARY TAXONOMY: {primary.get('desc')} (state={primary.get('state')}, license={primary.get('license')})")
        if prac:
            print(f"    PRACTICE ADDRESS: {format_address(prac[0])}")
        if phones:
            print(f"    PHONE: {phones[0]}")
        print_divider()


def print_nppes_raw(items: List[Dict[str, Any]]) -> None:
    """Full JSON-like dump for maximum detail (debug-style)."""
    if not items:
        print("No results found.")
        return
    for i, it in enumerate(items, 1):
        print(f"[{i}] {{")
        for k, v in it.items():
            print(f'  "{k}": {json.dumps(v, ensure_ascii=False)}')
        print("}")
        print_divider()


def _print_nppes_header(it: Dict[str, Any]) -> None:
    """Pretty header used by enriched mode."""
    primary = it.get("primary_taxonomy") or {}
    prac = it.get("practice_addresses") or []
    phones = it.get("phones") or []
    print(f"[1] NPI={it.get('npi')}  TYPE={it.get('enumeration_type')}  STATUS={it.get('status')}")
    print(f"    NAME: {it.get('name')}")
    if primary:
        print(f"    PRIMARY TAXONOMY: {primary.get('desc')} (state={primary.get('state')}, license={primary.get('license')})")
    if prac:
        print(f"    PRACTICE ADDRESS: {format_address(prac[0])}")
    if phones:
        print(f"    PHONE: {phones[0]}")


def print_nppes_enriched_with_cms(items: List[Dict[str, Any]], cms: Optional[CMSPDCClient]) -> None:
    """Enriched output: NPPES header + CMS affiliations + ratings."""
    if not items:
        print("No results found.")
        return

    for idx, it in enumerate(items, start=1):
        # Header
        primary = it.get("primary_taxonomy") or {}
        prac = it.get("practice_addresses") or []
        phones = it.get("phones") or []
        print(f"[{idx}] NPI={it.get('npi')}  TYPE={it.get('enumeration_type')}  STATUS={it.get('status')}")
        print(f"    NAME: {it.get('name')}")
        if primary:
            print(f"    PRIMARY TAXONOMY: {primary.get('desc')} (state={primary.get('state')}, license={primary.get('license')})")
        if prac:
            print(f"    PRACTICE ADDRESS: {format_address(prac[0])}")
        if phones:
            print(f"    PHONE: {phones[0]}")

        # If CMS client is not available, print fallback
        if not cms:
            print("    HOSPITAL AFFILIATIONS:")
            print("        (CMS client unavailable)")
            print_divider()
            continue

        # Collect affiliations from CMS by NPI
        npi = it.get("npi")
        affils = cms.get_hospital_affiliations_by_npi(str(npi)) if npi else []

        # Gather CCNs (valid 6-digit only), de-duplicate, cap the number to show
        ccns: List[str] = []
        cleaned: List[Dict[str, Optional[str]]] = []
        seen_ccn = set()
        for a in affils or []:
            ccn = a.get("ccn")
            nm = a.get("hospital_name")
            if ccn and re.fullmatch(r"\d{6}", str(ccn)):
                if ccn not in seen_ccn:
                    seen_ccn.add(ccn)
                    ccns.append(ccn)
            cleaned.append({"ccn": ccn if ccn else None, "hospital_name": nm if nm else None})

        MAX_SHOW = 30
        ccns = ccns[:MAX_SHOW]

        # Batch fetch hospital info (name/rating) for CCNs
        qual_map = cms.get_hospital_quality_by_ccns(tuple(ccns)) if ccns else {}

        # Print affiliations
        print("    HOSPITAL AFFILIATIONS:")
        if not cleaned:
            print("        (none found in CMS)")
        else:
            shown = 0
            for a in cleaned:
                if shown >= MAX_SHOW:
                    print(f"        ... (+{len(cleaned)-MAX_SHOW} more not shown)")
                    break
                ccn = a.get("ccn")
                hname = a.get("hospital_name")
                qual = qual_map.get(ccn) if ccn else None
                hname_from_qual = qual.get("hospital_name") if isinstance(qual, dict) else None
                display_name = hname or hname_from_qual or "(unknown hospital)"

                line = f"        - {display_name}"
                if ccn:
                    line += f" [CCN={ccn}]"
                star = qual.get("overall_rating") if isinstance(qual, dict) else None
                if star and str(star).strip().lower() not in {"", "not available", "not applicable"}:
                    line += f"  (⭐ {star})"
                print(line)
                shown += 1

        print_divider()


# =============================
# ClinicalTables output
# =============================
def print_ct_compact(rows: List[Dict[str, Any]]) -> None:
    """Compact display for ClinicalTables."""
    if not rows:
        print("No results found.")
        return
    for i, r in enumerate(rows, 1):
        print(f"[{i}] NPI={r.get('npi')}  NAME={r.get('name')}  TYPE={r.get('type')}")
        if r.get("practiceAddress"):
            print(f"    ADDRESS: {r.get('practiceAddress')}")
        print_divider()


def print_ct_detailed(rows: List[Dict[str, Any]]) -> None:
    """Detailed JSON-style display for ClinicalTables."""
    if not rows:
        print("No results found.")
        return
    for i, r in enumerate(rows, 1):
        print(f"[{i}] {{")
        for k, v in r.items():
            print(f'  "{k}": {json.dumps(v, ensure_ascii=False)}')
        print("}")
        print_divider()


# =============================
# CLI logic
# =============================
def run_nppes() -> None:
    """Run NPPES interactive search + optional CMS enrichment."""
    client = NPPESClient()
    try:
        cms = CMSPDCClient()
    except Exception:
        cms = None  # safe fallback

    print("\n[NPPES Search]")
    print("Leave fields blank to skip filters.")
    taxonomy = ask("Taxonomy description (e.g., Neurology)")
    state = ask("State code (2 letters, e.g., PA, NY)")
    city = ask("City")
    first = ask("First name")
    last = ask("Last name")
    org = ask("Organization name")
    number = ask("NPI number (10 digits)")
    postal = ask("Postal code (ZIP or ZIP+4)")
    enumeration_type = ask("Enumeration type (NPI-1 or NPI-2)")
    limit = ask_int("Maximum results", 5)
    skip = ask_int("Offset (skip)", 0)

    raw = client.search(
        taxonomy_description=taxonomy or None,
        state=state.upper() if state else None,
        city=city or None,
        first_name=first or None,
        last_name=last or None,
        organization_name=org or None,
        number=number or None,
        postal_code=postal or None,
        enumeration_type=enumeration_type if enumeration_type in {"NPI-1", "NPI-2"} else None,
        limit=limit,
        skip=skip,
    )

    items = NPPESClient.normalize(raw)
    print(f"\nNormalized results: {len(items)}\n")

    # Modes: compact / detailed(raw) / enriched(CMS)
    mode = ask_choice("Output mode", ["compact", "detailed", "enriched"], "detailed")
    if mode == "compact":
        print_nppes_compact(items)
    elif mode == "enriched":
        print_nppes_enriched_with_cms(items, cms)
    else:
        print_nppes_raw(items)


def run_clinicaltables() -> None:
    """Run ClinicalTables search."""
    client = ClinicalTablesClient()
    print("\n[NIH ClinicalTables Search]")
    term = ask("Search term (e.g., cardiology, ent, obgyn)")
    count = ask_int("Maximum results", 5)
    mode = ask_choice("Output mode", ["compact", "detailed", "enriched"], "detailed")

    results = client.search(term, count=count)
    if mode == "detailed":
        print_ct_detailed(results)
    else:
        print_ct_compact(results)


# =============================
# Entry point
# =============================
def main() -> None:
    print("=== Provider Search CLI (NPPES / ClinicalTables) ===")
    while True:
        print("\nWhat would you like to do?")
        print("  1) Search in NPPES (name, address, taxonomy, etc.)")
        print("  2) Search in NIH ClinicalTables (fast autocomplete)")
        print("  3) Exit")
        choice = ask_choice("Choice", ["1", "2", "3"], "3")
        if choice == "1":
            run_nppes()
        elif choice == "2":
            run_clinicaltables()
        elif choice == "3":
            print("Goodbye.")
            break


if __name__ == "__main__":
    main()
