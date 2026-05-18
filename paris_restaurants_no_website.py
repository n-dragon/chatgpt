"""
Collecte les restaurants à Paris sans site internet via l'API Google Maps Places.

Prérequis:
    pip install requests

Usage:
    export GOOGLE_MAPS_API_KEY="votre_clé_api"
    python paris_restaurants_no_website.py
"""

import os
import time
import json
import csv
import requests

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"

DETAIL_FIELDS = "name,formatted_address,formatted_phone_number,website,url,rating,user_ratings_total,opening_hours"

PARIS_ZONES = [
    "restaurants Paris 1er arrondissement",
    "restaurants Paris 2eme arrondissement",
    "restaurants Paris 3eme arrondissement",
    "restaurants Paris 4eme arrondissement",
    "restaurants Paris 5eme arrondissement",
    "restaurants Paris 6eme arrondissement",
    "restaurants Paris 7eme arrondissement",
    "restaurants Paris 8eme arrondissement",
    "restaurants Paris 9eme arrondissement",
    "restaurants Paris 10eme arrondissement",
    "restaurants Paris 11eme arrondissement",
    "restaurants Paris 12eme arrondissement",
    "restaurants Paris 13eme arrondissement",
    "restaurants Paris 14eme arrondissement",
    "restaurants Paris 15eme arrondissement",
    "restaurants Paris 16eme arrondissement",
    "restaurants Paris 17eme arrondissement",
    "restaurants Paris 18eme arrondissement",
    "restaurants Paris 19eme arrondissement",
    "restaurants Paris 20eme arrondissement",
]


def search_places(query: str, page_token: str = None) -> dict:
    params = {
        "query": query,
        "type": "restaurant",
        "key": API_KEY,
        "language": "fr",
    }
    if page_token:
        params["pagetoken"] = page_token
    response = requests.get(PLACES_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_place_details(place_id: str) -> dict:
    params = {
        "place_id": place_id,
        "fields": DETAIL_FIELDS,
        "key": API_KEY,
        "language": "fr",
    }
    response = requests.get(PLACES_DETAIL_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("result", {})


def collect_restaurants(max_per_zone: int = 60) -> list[dict]:
    """
    Parcourt les arrondissements de Paris et retourne les restaurants sans site web.
    max_per_zone : nombre max de restaurants analysés par arrondissement (multiple de 20).
    """
    seen_place_ids = set()
    results = []

    for zone in PARIS_ZONES:
        print(f"\n--- Recherche : {zone} ---")
        page_token = None
        zone_count = 0

        while zone_count < max_per_zone:
            data = search_places(zone, page_token)
            status = data.get("status")

            if status not in ("OK", "ZERO_RESULTS"):
                print(f"  Statut inattendu : {status}")
                break

            places = data.get("results", [])
            if not places:
                break

            for place in places:
                place_id = place["place_id"]
                if place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)
                zone_count += 1

                detail = get_place_details(place_id)
                time.sleep(0.05)  # respect rate limit

                if detail.get("website"):
                    continue  # a un site → on ignore

                restaurant = {
                    "name": detail.get("name", place.get("name", "")),
                    "address": detail.get("formatted_address", place.get("formatted_address", "")),
                    "phone": detail.get("formatted_phone_number", ""),
                    "google_maps_url": detail.get("url", ""),
                    "rating": detail.get("rating", ""),
                    "reviews": detail.get("user_ratings_total", ""),
                    "place_id": place_id,
                }
                results.append(restaurant)
                print(f"  [SANS SITE] {restaurant['name']} — {restaurant['address']}")

            page_token = data.get("next_page_token")
            if not page_token or zone_count >= max_per_zone:
                break

            time.sleep(2)  # next_page_token nécessite un délai

    return results


def save_results(restaurants: list[dict], json_path: str = "results.json", csv_path: str = "results.csv"):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(restaurants, f, ensure_ascii=False, indent=2)
    print(f"\nJSON sauvegardé : {json_path}")

    if restaurants:
        fieldnames = list(restaurants[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(restaurants)
        print(f"CSV sauvegardé  : {csv_path}")


def main():
    if not API_KEY:
        raise SystemExit("Erreur : variable d'environnement GOOGLE_MAPS_API_KEY non définie.")

    print("Collecte des restaurants parisiens sans site internet…")
    restaurants = collect_restaurants(max_per_zone=60)

    print(f"\n{'='*50}")
    print(f"Total trouvé : {len(restaurants)} restaurant(s) sans site web")

    save_results(restaurants)


if __name__ == "__main__":
    main()
