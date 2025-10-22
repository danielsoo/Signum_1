import requests

BASE = "https://npiregistry.cms.hhs.gov/api/"

def npi_search(first_name=None, last_name=None, taxonomy_description=None, city=None, state=None, limit=10):
    params = {"version": "2.1", "limit": limit}
    if first_name:
        params["first_name"] = first_name
    if last_name:
        params["last_name"] = last_name
    if taxonomy_description:
        params["taxonomy_description"] = taxonomy_description
    if city:
        params["city"] = city
    if state:
        params["state"] = state

    r = requests.get(BASE, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()

    results = []
    for item in j.get("results", []):
        basic = item.get("basic", {})
        addresses = item.get("addresses", [])
        tax = item.get("taxonomies", [])
        results.append({
            "npi": item.get("number"),
            "first_name": basic.get("first_name"),
            "last_name": basic.get("last_name"),
            "name": basic.get("name"),
            "credential": basic.get("credential"),
            "gender": basic.get("gender"),
            "enumeration_date": basic.get("enumeration_date"),
            "last_updated": basic.get("last_updated"),
            "taxonomies": [{"code": t.get("code"), "desc": t.get("desc")} for t in tax],
            "addresses": [{
                "address_purpose": a.get("address_purpose"),
                "address_1": a.get("address_1"),
                "address_2": a.get("address_2"),
                "city": a.get("city"),
                "state": a.get("state"),
                "postal_code": a.get("postal_code"),
                "telephone_number": a.get("telephone_number"),
                "latitude": a.get("latitude"),
                "longitude": a.get("longitude"),
            } for a in addresses],
            "practice_location": next((a for a in addresses if a.get("address_purpose") == "LOCATION"), None),
        })

    return {"count": len(results), "results": results}

def npi_get(npi: str):
    params = {"version": "2.1", "number": npi}
    r = requests.get(BASE, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()
    if not j.get("results"):
        return {"found": False, "result": None}
    item = j["results"][0]
    basic = item.get("basic", {})
    addresses = item.get("addresses", [])
    tax = item.get("taxonomies", [])
    return {
        "found": True,
        "result": {
            "npi": item.get("number"),
            "first_name": basic.get("first_name"),
            "last_name": basic.get("last_name"),
            "name": basic.get("name"),
            "credential": basic.get("credential"),
            "gender": basic.get("gender"),
            "enumeration_date": basic.get("enumeration_date"),
            "last_updated": basic.get("last_updated"),
            "taxonomies": [{"code": t.get("code"), "desc": t.get("desc")} for t in tax],
            "addresses": [{
                "address_purpose": a.get("address_purpose"),
                "address_1": a.get("address_1"),
                "address_2": a.get("address_2"),
                "city": a.get("city"),
                "state": a.get("state"),
                "postal_code": a.get("postal_code"),
                "telephone_number": a.get("telephone_number"),
                "latitude": a.get("latitude"),
                "longitude": a.get("longitude"),
            } for a in addresses],
            "practice_location": next((a for a in addresses if a.get("address_purpose") == "LOCATION"), None),
        }
    }
