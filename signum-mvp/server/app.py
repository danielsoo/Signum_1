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
