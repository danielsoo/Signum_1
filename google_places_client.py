from typing import Any, Dict, List, Optional, Tuple
import os, re, time
import requests

# -----------------------------
# (1) Rate Limiter (토큰버킷)
# -----------------------------
class CompositeLimiter:
    def __init__(self, rps: float = 8.0, bucket: int = 8, daily_quota: int = 10000):
        self.capacity = max(1, bucket)
        self.tokens = self.capacity
        self.refill_rate = max(0.1, rps)
        self.last = time.time()
        self.daily_quota = daily_quota
        self.spent_today = 0
        self.day = time.strftime('%Y-%m-%d')
    def acquire(self, cost: int = 1):
        today = time.strftime('%Y-%m-%d')
        if today != self.day:
            self.day, self.spent_today = today, 0
        if self.spent_today + cost > self.daily_quota:
            raise RuntimeError('Daily quota exceeded')
        while True:
            now = time.time()
            dt = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + dt * self.refill_rate)
            if self.tokens >= cost:
                self.tokens -= cost
                self.spent_today += cost
                return
            time.sleep(max(0.01, (cost - self.tokens) / self.refill_rate))

# -----------------------------
# (2) Http Client
# -----------------------------
class HttpClient:
    def get(self, url: str, params: Optional[Dict[str, Any]] = None):
        return requests.get(url, params=params, timeout=20)
    @staticmethod
    def safe_json(resp):
        try:
            return resp.json()
        except Exception:
            return None

# -----------------------------
# (3) Google Places Client
# -----------------------------
def _strip_zip(postal: Optional[str]) -> Optional[str]:
    if not postal: return None
    m = re.match(r"(\\d{5})(?:-\\d{4})?", postal)
    return m.group(1) if m else postal

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _norm_addr(addr: Dict[str, Any]) -> Dict[str, Optional[str]]:
    return {
        "line1": addr.get("address_1") or addr.get("line1"),
        "city": addr.get("city"),
        "state": addr.get("state"),
        "postal": _strip_zip(addr.get("postal_code") or addr.get("postal"))
    }

class GooglePlacesClient:
    TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise RuntimeError("Google Places API key required (set GOOGLE_MAPS_API_KEY)")
        self.http = HttpClient()
        self.limiter = CompositeLimiter()

    def text_search(self, query: str) -> Dict[str, Any]:
        self.limiter.acquire()
        resp = self.http.get(self.TEXT_SEARCH_URL, {"query": query, "key": self.api_key})
        return self.http.safe_json(resp) or {}

    def place_details(self, place_id: str) -> Dict[str, Any]:
        self.limiter.acquire()
        fields = [
            "place_id","name","formatted_address","geometry/location","rating","user_ratings_total",
            "reviews","photos","opening_hours","website","formatted_phone_number","types","url"
        ]
        resp = self.http.get(self.DETAILS_URL, {"place_id": place_id, "fields": ",".join(fields), "key": self.api_key})
        return self.http.safe_json(resp) or {}

    def build_photo_url(self, ref: str, max_width: int = 1200) -> str:
        return f"{self.PHOTO_URL}?maxwidth={max_width}&photoreference={ref}&key={self.api_key}"

    def find_best_place_id(self, name: str, addr: Dict[str, Any]) -> Optional[str]:
        a = _norm_addr(addr)
        query = " ".join([_norm(p) for p in [name, a.get("line1"), a.get("city"), a.get("state"), a.get("postal")] if _norm(p)])
        data = self.text_search(query)
        results = data.get("results") or []
        return results[0]["place_id"] if results else None

    def get_normalized_details(self, place_id: str) -> Dict[str, Any]:
        data = self.place_details(place_id)
        res = data.get("result") or {}
        photos = []
        for ph in res.get("photos", [])[:5]:
            ref = ph.get("photo_reference")
            if ref:
                photos.append({"url": self.build_photo_url(ref), "attr": ph.get("html_attributions")})
        reviews = []
        for rv in res.get("reviews", [])[:5]:
            reviews.append({"author": rv.get("author_name"), "rating": rv.get("rating"), "text": rv.get("text")})
        return {
            "name": res.get("name"),
            "rating": res.get("rating"),
            "reviews": reviews,
            "photos": photos,
            "phone": res.get("formatted_phone_number"),
            "website": res.get("website"),
            "url": res.get("url"),
        }
