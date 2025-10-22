import math
from typing import List, Dict, Any, Optional
from .npi import npi_search
from .yelp import yelp_match

GOAL_SPECIALTIES = {
    "cardiac_checkup": ["Cardiology"],
    "diabetes_consult": ["Endocrinology, Diabetes & Metabolism"],
    "annual_physical": ["Family Medicine", "Internal Medicine"],
    "derm_rash": ["Dermatology"],
}

EARTH_RADIUS_KM = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    to_rad = math.radians
    dlat = to_rad(lat2 - lat1)
    dlon = to_rad(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c

def recommend(
    goal: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    min_rating: float = 0.0,
    min_reviews: int = 0,
    specialties_filter: Optional[List[str]] = None,
    sort: str = "distance"
) -> Dict[str, Any]:
    specialties = GOAL_SPECIALTIES.get(goal, [])
    if specialties_filter:
        specialties = specialties_filter if not specialties else [s for s in specialties if s in specialties_filter] or specialties_filter

    candidates = []
    seen_npi = set()
    search_specs = specialties or [None]

    for spec in search_specs:
        res = npi_search(
            taxonomy_description=spec,
            city=city,
            state=state,
            limit=25,
            first_name=None,
            last_name=None,
        )
        for p in res.get("results", []):
            npi = p.get("npi")
            if not npi or npi in seen_npi:
                continue
            seen_npi.add(npi)

            loc = p.get("practice_location") or {}
            plat = loc.get("latitude")
            plng = loc.get("longitude")
            if isinstance(plat, str):
                try: plat = float(plat)
                except: plat = None
            if isinstance(plng, str):
                try: plng = float(plng)
                except: plng = None

            item = {
                "npi": npi,
                "name": p.get("name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                "taxonomies": p.get("taxonomies", []),
                "practice_location": {
                    "address_1": loc.get("address_1"),
                    "city": loc.get("city"),
                    "state": loc.get("state"),
                    "postal_code": loc.get("postal_code"),
                    "telephone_number": loc.get("telephone_number"),
                    "latitude": plat,
                    "longitude": plng,
                },
                "yelp": None,
                "distance_km": None,
                "specialty": None,
            }

            if item["taxonomies"]:
                item["specialty"] = item["taxonomies"][0].get("desc")

            if lat is not None and lng is not None and plat is not None and plng is not None:
                item["distance_km"] = haversine_km(lat, lng, plat, plng)

            candidates.append(item)

    enriched = []
    for c in candidates:
        loc = c.get("practice_location") or {}
        if not (c.get("name") and loc.get("address_1") and loc.get("city") and loc.get("state") and loc.get("postal_code")):
            enriched.append(c)
            continue
        y = yelp_match(
            name=c["name"],
            address1=loc["address_1"],
            city=loc["city"],
            state=loc["state"],
            postal_code=loc["postal_code"],
            phone=loc.get("telephone_number")
        )
        if y.get("results"):
            c["yelp"] = y["results"][0]
        enriched.append(c)

    def pass_filters(x):
        if specialties_filter:
            sp = x.get("specialty")
            if sp and sp not in specialties_filter:
                return False
        if radius_km is not None and x.get("distance_km") is not None:
            if x["distance_km"] > radius_km:
                return False
        y = x.get("yelp") or {}
        if y:
            if y.get("rating") is not None and y["rating"] < min_rating:
                return False
            if y.get("review_count") is not None and y["review_count"] < min_reviews:
                return False
        return True

    filtered = [x for x in enriched if pass_filters(x)]

    def sort_key(x):
        if sort == "rating":
            return -(x.get("yelp", {}).get("rating") or -1)
        if sort == "reviews":
            return -(x.get("yelp", {}).get("review_count") or -1)
        if sort == "specialty":
            return x.get("specialty") or "zzz"
        d = x.get("distance_km")
        return 1e9 if d is None else d

    filtered.sort(key=sort_key)

    return {"count": len(filtered), "results": filtered}
