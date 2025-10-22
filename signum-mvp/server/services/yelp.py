import os
import requests

API_SEARCH = "https://api.yelp.com/v3/businesses/search"
API_MATCH = "https://api.yelp.com/v3/businesses/matches"
API_BUSINESS = "https://api.yelp.com/v3/businesses/{}"

def _headers():
    api_key = os.getenv("YELP_API_KEY")
    if not api_key:
        return None
    return {"Authorization": f"Bearer {api_key}"}

def yelp_search(term, location, limit=10, sort_by="best_match"):
    headers = _headers()
    if not headers:
        return {"error": "Missing YELP_API_KEY", "results": []}

    params = {
        "term": term or "doctor",
        "location": location or "Philadelphia, PA",
        "limit": limit,
        "sort_by": sort_by,
        "categories": "health,medical",
    }

    r = requests.get(API_SEARCH, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()

    results = []
    for b in j.get("businesses", []):
        results.append({
            "id": b.get("id"),
            "name": b.get("name"),
            "rating": b.get("rating"),
            "review_count": b.get("review_count"),
            "phone": b.get("phone"),
            "display_phone": b.get("display_phone"),
            "location": b.get("location"),
            "coordinates": b.get("coordinates"),
            "url": b.get("url"),
        })

    return {"count": len(results), "results": results}

def yelp_match(name, address1, city, state, postal_code, phone=None, country="US"):
    headers = _headers()
    if not headers:
        return {"error": "Missing YELP_API_KEY", "results": []}
    params = {
        "name": name,
        "address1": address1,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country,
        "match_threshold": "strict"
    }
    if phone:
        params["phone"] = "".join([c for c in str(phone) if c.isdigit()])

    r = requests.get(API_MATCH, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()

    details = []
    for m in j.get("businesses", []):
        bid = m.get("id")
        if not bid:
            continue
        d = requests.get(API_BUSINESS.format(bid), headers=headers, timeout=15).json()
        details.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "rating": d.get("rating"),
            "review_count": d.get("review_count"),
            "phone": d.get("phone"),
            "display_phone": d.get("display_phone"),
            "location": d.get("location"),
            "coordinates": d.get("coordinates"),
            "url": d.get("url")
        })
    return {"count": len(details), "results": details}
