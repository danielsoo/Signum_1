#!/usr/bin/env bash
set -euo pipefail

# 루트
mkdir -p signum-mvp
cd signum-mvp

################################
# server (Flask)
################################
mkdir -p server/services

# server/requirements.txt
cat > server/requirements.txt <<'EOF'
Flask==3.0.2
Flask-Cors==4.0.1
python-dotenv==1.0.1
requests==2.32.3
EOF

# server/.env.example
cat > server/.env.example <<'EOF'
FLASK_ENV=development
YELP_API_KEY=YOUR_YELP_FUSION_API_KEY
PORT=5000
EOF

# server/services/npi.py
cat > server/services/npi.py <<'EOF'
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
EOF

# server/services/yelp.py
cat > server/services/yelp.py <<'EOF'
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
EOF

# server/services/recommend.py
cat > server/services/recommend.py <<'EOF'
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
EOF

# server/app.py
cat > server/app.py <<'EOF'
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os

from services.npi import npi_search, npi_get
from services.yelp import yelp_search, yelp_match
from services.recommend import recommend

def create_app():
    load_dotenv()
    app = Flask(__name__)
    CORS(app)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/providers/search")
    def providers_search():
        params = {
            "first_name": request.args.get("first_name"),
            "last_name": request.args.get("last_name"),
            "taxonomy_description": request.args.get("specialty"),
            "city": request.args.get("city"),
            "state": request.args.get("state"),
            "limit": request.args.get("limit", 10, type=int),
        }
        data = npi_search(**params)
        return jsonify(data)

    @app.get("/api/providers/by-npi")
    def provider_by_npi():
        npi = request.args.get("npi")
        if not npi:
            return jsonify({"error": "npi required"}), 400
        return jsonify(npi_get(npi))

    @app.get("/api/places/yelp/search")
    def yelp_search_endpoint():
        term = request.args.get("term")
        location = request.args.get("location")
        limit = request.args.get("limit", 10)
        sort_by = request.args.get("sort_by", "best_match")
        data = yelp_search(term=term, location=location, limit=limit, sort_by=sort_by)
        return jsonify(data)

    @app.get("/api/places/yelp/match")
    def yelp_match_endpoint():
        name = request.args.get("name")
        address1 = request.args.get("address1")
        city = request.args.get("city")
        state = request.args.get("state")
        postal_code = request.args.get("postal_code")
        phone = request.args.get("phone")
        if not all([name, address1, city, state, postal_code]):
            return jsonify({"error": "name, address1, city, state, postal_code required"}), 400
        data = yelp_match(name, address1, city, state, postal_code, phone=phone)
        return jsonify(data)

    @app.get("/api/recommendations")
    def recommendations():
        goal = request.args.get("goal", "annual_physical")
        city = request.args.get("city")
        state = request.args.get("state")
        lat = request.args.get("lat", type=float)
        lng = request.args.get("lng", type=float)
        radius_km = request.args.get("radius_km", type=float)
        min_rating = request.args.get("min_rating", default=0.0, type=float)
        min_reviews = request.args.get("min_reviews", default=0, type=int)
        sort = request.args.get("sort", default="distance")
        specialties_filter = request.args.getlist("specialty") or None
        data = recommend(
            goal=goal, city=city, state=state, lat=lat, lng=lng,
            radius_km=radius_km, min_rating=min_rating, min_reviews=min_reviews,
            specialties_filter=specialties_filter, sort=sort
        )
        return jsonify(data)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), debug=True)
EOF

################################
# client (React + Vite)
################################
mkdir -p client/src

# client/index.html
cat > client/index.html <<'EOF'
<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SIGNUM MVP</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF

# client/package.json
cat > client/package.json <<'EOF'
{
  "name": "signum-client",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.28",
    "@types/react-dom": "^18.2.12",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.3",
    "vite": "^5.0.0"
  }
}
EOF

# client/tsconfig.json
cat > client/tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "jsx": "react-jsx",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "noEmit": true,
    "strict": true
  },
  "include": ["src"]
}
EOF

# client/vite.config.ts
cat > client/vite.config.ts <<'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
})
EOF

# client/src/main.tsx
cat > client/src/main.tsx <<'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
EOF

# client/src/App.tsx
cat > client/src/App.tsx <<'EOF'
import { useState } from 'react'

export default function App() {
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    specialty: '',
    city: '',
    state: 'PA',
  })
  const [providers, setProviders] = useState<any[]>([])
  const [businesses, setBusinesses] = useState<any[]>([])
  const [recs, setRecs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [goal, setGoal] = useState('annual_physical')
  const [lat, setLat] = useState<string>('') 
  const [lng, setLng] = useState<string>('') 
  const [radiusKm, setRadiusKm] = useState<string>('')
  const [minRating, setMinRating] = useState<string>('')
  const [minReviews, setMinReviews] = useState<string>('')
  const [sort, setSort] = useState<'distance'|'rating'|'reviews'|'specialty'>('distance')

  const searchProviders = async () => {
    setLoading(true); setError(null)
    try {
      const params = new URLSearchParams()
      Object.entries(form).forEach(([k, v]) => v && params.append(k, String(v)))
      const res = await fetch(`/api/providers/search?${params.toString()}`)
      if (!res.ok) throw new Error('NPI search failed')
      const json = await res.json()
      setProviders(json.results || [])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const searchYelp = async () => {
    setLoading(true); setError(null)
    try {
      const term = form.specialty || 'doctor'
      const location = [form.city, form.state].filter(Boolean).join(', ')
      const res = await fetch(`/api/places/yelp/search?term=${encodeURIComponent(term)}&location=${encodeURIComponent(location)}`)
      if (!res.ok) throw new Error('Yelp search failed')
      const json = await res.json()
      setBusinesses(json.results || [])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function fetchRecs(){
    setLoading(true); setError(null)
    try{
      const params = new URLSearchParams()
      params.set('goal', goal)
      if (form.city) params.set('city', form.city)
      if (form.state) params.set('state', form.state)
      if (lat) params.set('lat', lat)
      if (lng) params.set('lng', lng)
      if (radiusKm) params.set('radius_km', radiusKm)
      if (minRating) params.set('min_rating', minRating)
      if (minReviews) params.set('min_reviews', minReviews)
      params.set('sort', sort)
      const res = await fetch(`/api/recommendations?${params.toString()}`)
      if(!res.ok) throw new Error('recommendations failed')
      const json = await res.json()
      setRecs(json.results || [])
    }catch(e:any){
      setError(e.message)
    }finally{ setLoading(false) }
  }

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: 16 }}>
      <h1>SIGNUM — Provider & Reviews MVP</h1>

      <h2>Search (NPI & Yelp)</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
        <input placeholder="First name" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} />
        <input placeholder="Last name" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} />
        <input placeholder="Specialty (e.g., Cardiology)" value={form.specialty} onChange={e => setForm({ ...form, specialty: e.target.value })} />
        <input placeholder="City" value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} />
        <input placeholder="State (e.g., PA)" value={form.state} onChange={e => setForm({ ...form, state: e.target.value })} />
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button onClick={searchProviders} disabled={loading}>Search NPI Providers</button>
        <button onClick={searchYelp} disabled={loading}>Search Yelp Reviews</button>
      </div>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      <h3 style={{ marginTop: 24 }}>NPI Providers</h3>
      {providers.map((p, idx) => (
        <div key={p.npi || idx} style={{ border: '1px solid #ccc', borderRadius: 8, padding: 12, marginBottom: 8 }}>
          <strong>{p.name || `${p.first_name || ''} ${p.last_name || ''}`}</strong> {p.taxonomies?.[0]?.desc ? `— ${p.taxonomies[0].desc}` : ''}
          <div>NPI: {p.npi}</div>
          {p.practice_location && (
            <div>
              {p.practice_location.city}, {p.practice_location.state} {p.practice_location.postal_code} — {p.practice_location.telephone_number}
            </div>
          )}
        </div>
      ))}

      <h3 style={{ marginTop: 24 }}>Yelp Businesses</h3>
      {businesses.map((b, idx) => (
        <div key={b.id || idx} style={{ border: '1px solid #ccc', borderRadius: 8, padding: 12, marginBottom: 8 }}>
          <strong>{b.name}</strong> — rating {b.rating} ({b.review_count})
          <div>{b.location?.display_address?.join(', ')}</div>
          {b.url && <a href={b.url} target="_blank">Open on Yelp</a>}
        </div>
      ))}

      <div style={{ marginTop: 24, padding: 12, border: '1px solid #ddd', borderRadius: 8 }}>
        <h2>Goal-based Recommendations</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          <select value={goal} onChange={e=>setGoal(e.target.value)}>
            <option value="annual_physical">Annual Physical</option>
            <option value="cardiac_checkup">Cardiac Checkup</option>
            <option value="diabetes_consult">Diabetes Consult</option>
            <option value="derm_rash">Dermatology (Rash)</option>
          </select>
          <input placeholder="Lat" value={lat} onChange={e=>setLat(e.target.value)} />
          <input placeholder="Lng" value={lng} onChange={e=>setLng(e.target.value)} />
          <input placeholder="Radius (km)" value={radiusKm} onChange={e=>setRadiusKm(e.target.value)} />
          <input placeholder="Min rating (e.g., 4)" value={minRating} onChange={e=>setMinRating(e.target.value)} />
          <input placeholder="Min reviews (e.g., 20)" value={minReviews} onChange={e=>setMinReviews(e.target.value)} />
          <select value={sort} onChange={e=>setSort(e.target.value as any)}>
            <option value="distance">Sort: Distance</option>
            <option value="rating">Sort: Rating</option>
            <option value="reviews">Sort: Reviews</option>
            <option value="specialty">Sort: Specialty</option>
          </select>
        </div>
        <div style={{ display:'flex', gap:8, marginTop:8 }}>
          <button onClick={fetchRecs} disabled={loading}>Recommend</button>
        </div>

        {recs.map((r, i)=> (
          <div key={r.npi || i} style={{ border:'1px solid #ccc', borderRadius:8, padding:12, marginTop:8 }}>
            <strong>{r.name}</strong>{r.specialty ? ` — ${r.specialty}` : ''}
            {typeof r.distance_km === 'number' && (
              <div>Distance: {r.distance_km.toFixed(1)} km</div>
            )}
            {r.practice_location && (
              <div>
                {r.practice_location.city}, {r.practice_location.state} {r.practice_location.postal_code}
                {r.practice_location.telephone_number ? ` — ${r.practice_location.telephone_number}` : ''}
              </div>
            )}
            {r.yelp && (
              <div>
                Yelp: ⭐ {r.yelp.rating} ({r.yelp.review_count}) — <a href={r.yelp.url} target="_blank">Open</a>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
EOF

# README.md
cat > README.md <<'EOF'
# SIGNUM Provider & Reviews MVP (Flask + React)

## Prereqs
- Python 3.10+
- Node.js 18+

## 1) Backend
```bash
cd server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate (use Git Bash/WSL)
pip install -r requirements.txt
cp .env.example .env        # put your YELP_API_KEY in .env
python app.py               # runs on http://localhost:5000

