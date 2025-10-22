#free_provider_apis/google/cli_google.py

from __future__ import annotations
from typing import List

from pathlib import Path
from typing import List

# .env 로드: 이 파일의 부모(= free_provider_apis/)에 있는 .env
try:
    from dotenv import load_dotenv
    ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
    # print(f"[DEBUG] load .env -> {ENV_PATH}")  # 필요하면 확인용
    load_dotenv(ENV_PATH)
except Exception:
    pass


# 절대 임포트(패키지) → 실패 시 로컬 모듈 폴백
try:
    import free_provider_apis.google.places_client_v1 as pc
    import free_provider_apis.google.usage_tracker as ut
    import free_provider_apis.google.feature_flags as ff
except Exception:
    import places_client_v1 as pc
    import usage_tracker as ut
    import feature_flags as ff

PlacesV1Client = pc.PlacesV1Client
UsageTracker   = ut.UsageTracker
enable         = ff.enable
disable        = ff.disable
is_on          = ff.is_on
load_from_env  = ff.load_from_env
all_flags      = ff.all

STAR_FILLED = "★"
STAR_EMPTY = "☆"

FEATURE_NAMES = {
    "rating","reviews","photos_meta","photo_media",
    "phone","website","text_search","details_essentials"
}

def stars(v: float) -> str:
    if v is None: return ""
    v = max(0.0, min(5.0, round(v * 2) / 2))
    filled = int(v)
    return (STAR_FILLED * filled) + (STAR_EMPTY * (5 - filled))

def show_usage(tracker: UsageTracker) -> None:
    snap = tracker.snapshot()
    order = ("text_search_pro", "place_details_essentials", "place_details_enterprise", "place_details_photos")
    line = []
    for key in order:
        used = snap[key]["used"]; limit = snap[key]["limit"]
        line.append(f"{key}: {used}/{limit}")
    print("Usage — " + " · ".join(line))

def show_flags() -> None:
    flags = all_flags()
    items = [f"{k}={'on' if v else 'off'}" for k, v in sorted(flags.items())]
    print("Flags — " + " · ".join(items))

def run_google_enrichment() -> None:
    load_from_env()   # FREE_FEATURES로 초기화 가능

    tracker = UsageTracker()
    allow_enterprise = False   # 기본: 무료 모드
    strict_mode = True         # 기본: 엄격 모드(차단)
    client = PlacesV1Client(allow_enterprise=allow_enterprise, tracker=tracker, strict=strict_mode)

    print("Commands:")
    print("  /on <feature>      e.g. /on rating, /on reviews")
    print("  /off <feature>     e.g. /off photos_meta")
    print("  /enable            (master) allow enterprise fields")
    print("  /disable           (master) disallow enterprise fields")
    print("  /strict on|off     strict=True: 차단, False: 자동 필터링")
    print("  /flags             현재 feature flags 보기")
    print("  /usage             사용량 보기")
    print("  /quit              종료")

    while True:
        cmd = input("\nHospital name (or command): ").strip()
        if not cmd: continue
        low = cmd.lower()

        if low in ("/q", "/quit", "q", "quit"):
            print("Bye."); return

        # ----- commands -----
        if low.startswith("/on "):
            feat = cmd.split(" ", 1)[1].strip()
            if feat in FEATURE_NAMES:
                enable(feat); print(f"✅ feature '{feat}' = ON")
            else:
                print(f"Unknown feature: {feat}")
            continue

        if low.startswith("/off "):
            feat = cmd.split(" ", 1)[1].strip()
            if feat in FEATURE_NAMES:
                disable(feat); print(f"✅ feature '{feat}' = OFF")
            else:
                print(f"Unknown feature: {feat}")
            continue

        if low in ("/enable", "enable"):
            allow_enterprise = True
            client.allow_enterprise = True
            print("✅ Enterprise fields ENABLED."); continue

        if low in ("/disable", "disable"):
            allow_enterprise = False
            client.allow_enterprise = False
            print("✅ Enterprise fields DISABLED."); continue

        if low.startswith("/strict"):
            arg = (cmd.split(" ", 1)[1].strip().lower() if " " in cmd else "")
            if arg in ("on","true","1"):
                strict_mode = True; client.strict = True
            elif arg in ("off","false","0"):
                strict_mode = False; client.strict = False
            else:
                print("Usage: /strict on|off"); continue
            print(f"✅ strict mode = {client.strict}"); continue

        if low in ("/usage", "usage"):
            show_usage(tracker); continue

        if low in ("/flags", "flags"):
            show_flags(); continue

        # ----- search flow -----
        name = cmd
        line1 = input("Address line1 (optional): ").strip()
        city = input("City (optional): ").strip()
        state = input("State (optional): ").strip()
        postal = input("ZIP (optional): ").strip()

        # Text Search (Pro-safe fields)
        if not is_on("text_search"):
            print("❌ text_search is OFF (enable with /on text_search)"); continue

        parts = [name, line1, city, state, postal]
        query = " ".join([p for p in parts if p])
        data = client.search_text(query, fields=["places.id", "places.displayName", "places.formattedAddress"])
        places = data.get("places") or []
        if not places:
            print("❌ No matching place found."); continue

        cand = places[0]
        pid = cand.get("id")

        # Details — Essentials + 켜진 엔터프라이즈만
        fields: List[str] = ["id", "displayName", "formattedAddress", "location", "shortFormattedAddress"]
        if allow_enterprise:
            flag = ff.is_on
            if flag("rating"):      fields += ["rating", "userRatingCount"]
            if flag("reviews"):     fields += ["reviews"]
            if flag("phone"):       fields += ["nationalPhoneNumber", "internationalPhoneNumber"]
            if flag("website"):     fields += ["websiteUri"]
            if flag("photos_meta"): fields += ["photos"]

        det = client.place_details(pid, fields=fields)
        name_txt = (det.get("displayName") or {}).get("text") or "(unknown)"
        addr = det.get("formattedAddress") or det.get("shortFormattedAddress") or "—"

        print(f"\n{name_txt}")
        print(f"Address: {addr}")

        # 표시 — 켜진 항목만 보여주고, 아니면 LOCKED
        if allow_enterprise and is_on("rating"):
            r = det.get("rating"); rc = det.get("userRatingCount") or 0
            print(f"Rating: {stars(r)} ({r}/5) · {rc} ratings" if r is not None else "Rating: —")
        else:
            print("Rating: [LOCKED] Paid feature (temporarily disabled)")

        if allow_enterprise and is_on("reviews"):
            revs = (det.get("reviews") or [])[:3]
            if not revs:
                print("Reviews: No recent reviews.")
            else:
                print("Reviews:")
                for rv in revs:
                    author = rv.get("authorAttribution", {}).get("displayName") or rv.get("authorName") or "Anonymous"
                    rr = rv.get("rating")
                    txt = (rv.get("originalText") or {}).get("text") or rv.get("text") or ""
                    txt = txt.strip().replace("\n", " ")
                    if len(txt) > 200: txt = txt[:200] + "…"
                    star = stars(float(rr)) if rr is not None else ""
                    suffix = f" ({rr}/5)" if rr is not None else ""
                    print(f" • {author} · {star}{suffix} — {txt}")
        else:
            print("Reviews: [LOCKED] Paid feature (temporarily disabled)")

        if allow_enterprise and is_on("photos_meta"):
            ph = det.get("photos") or []
            if ph:
                print(f"Photos: {len(ph)} metadata items (media via server proxy counts toward place_details_photos)")
            else:
                print("Photos: —")
        else:
            print("Photos: [LOCKED] Paid feature (temporarily disabled)")

        # 하단 사용량 배지
        show_usage(tracker)

if __name__ == "__main__":
    run_google_enrichment()
