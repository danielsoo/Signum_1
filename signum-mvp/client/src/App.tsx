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
