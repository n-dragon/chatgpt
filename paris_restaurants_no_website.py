"""
Collecte les restaurants à Paris sans site internet via l'API Google Maps Places.
Pour chaque restaurant, télécharge les photos et les analyse via Claude (vision)
pour décrire le style et l'ambiance.

Prérequis:
    pip install requests anthropic

Usage:
    export GOOGLE_MAPS_API_KEY="votre_clé_api"
    export ANTHROPIC_API_KEY="votre_clé_anthropic"
    python paris_restaurants_no_website.py
"""

import os
import time
import json
import csv
import base64
import requests
import anthropic

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
ANTHROPIC_CLIENT = anthropic.Anthropic()

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"

MAX_PHOTOS_PER_RESTAURANT = 3

DETAIL_FIELDS = (
    "name,"
    "formatted_address,"
    "formatted_phone_number,"
    "website,"
    "url,"
    "rating,"
    "user_ratings_total,"
    "price_level,"
    "types,"
    "editorial_summary,"
    "reviews,"
    "opening_hours,"
    "business_status,"
    "serves_breakfast,"
    "serves_brunch,"
    "serves_lunch,"
    "serves_dinner,"
    "serves_beer,"
    "serves_wine,"
    "serves_vegetarian_food,"
    "dine_in,"
    "takeout,"
    "delivery,"
    "reservable,"
    "wheelchair_accessible_entrance,"
    "photos"
)

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


def fetch_photo_bytes(photo_reference: str, max_width: int = 800) -> bytes | None:
    """Télécharge une photo Google Maps et retourne ses octets bruts."""
    params = {
        "maxwidth": max_width,
        "photo_reference": photo_reference,
        "key": API_KEY,
    }
    try:
        response = requests.get(PLACES_PHOTO_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        print(f"    [photo] erreur téléchargement : {exc}")
        return None


def analyze_ambiance(restaurant_name: str, photos_bytes: list[bytes]) -> str:
    """
    Envoie les photos d'un restaurant à Claude (vision) et retourne
    une description du style et de l'ambiance.
    """
    if not photos_bytes:
        return ""

    image_blocks = []
    for raw in photos_bytes:
        b64 = base64.standard_b64encode(raw).decode("utf-8")
        image_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            },
        })

    image_blocks.append({
        "type": "text",
        "text": (
            f"Voici {len(photos_bytes)} photo(s) du restaurant « {restaurant_name} » à Paris.\n"
            "Décris en 3 à 5 phrases courtes le style et l'ambiance de ce restaurant : "
            "type de décor (moderne, rustique, bistrot, gastronomique…), atmosphère "
            "(intime, animée, familiale…), clientèle probable, et tout détail visuel "
            "notable (luminosité, couleurs, matériaux, terrasse, etc.).\n"
            "Réponds uniquement en français, de manière factuelle et concise."
        ),
    })

    try:
        response = ANTHROPIC_CLIENT.messages.create(
            model="claude-opus-4-7",
            max_tokens=512,
            messages=[{"role": "user", "content": image_blocks}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        print(f"    [claude] erreur analyse ambiance : {exc}")
        return ""


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

                price_map = {0: "gratuit", 1: "€", 2: "€€", 3: "€€€", 4: "€€€€"}
                price_level = detail.get("price_level")

                # Avis clients : on garde le texte des 5 premiers avis
                raw_reviews = detail.get("reviews") or []
                customer_reviews = [
                    {
                        "author": r.get("author_name", ""),
                        "rating": r.get("rating", ""),
                        "text": r.get("text", ""),
                        "time": r.get("relative_time_description", ""),
                    }
                    for r in raw_reviews
                ]

                # Résumé éditorial Google (disponible sur certains lieux)
                editorial = detail.get("editorial_summary", {})

                # Types Google → catégories lisibles
                types = detail.get("types") or []
                readable_types = [t.replace("_", " ") for t in types if t not in ("point_of_interest", "establishment", "food")]

                # Horaires : liste des jours
                opening = detail.get("opening_hours", {})
                hours = opening.get("weekday_text", [])

                # Photos → analyse ambiance via Claude
                raw_photos = detail.get("photos") or []
                photos_bytes = []
                for photo_info in raw_photos[:MAX_PHOTOS_PER_RESTAURANT]:
                    ref = photo_info.get("photo_reference", "")
                    if ref:
                        img = fetch_photo_bytes(ref)
                        if img:
                            photos_bytes.append(img)
                        time.sleep(0.1)

                ambiance = analyze_ambiance(
                    detail.get("name", place.get("name", "")),
                    photos_bytes,
                )

                restaurant = {
                    # Identité
                    "place_id": place_id,
                    "name": detail.get("name", place.get("name", "")),
                    "address": detail.get("formatted_address", place.get("formatted_address", "")),
                    "phone": detail.get("formatted_phone_number", ""),
                    "google_maps_url": detail.get("url", ""),
                    "business_status": detail.get("business_status", ""),
                    # Activité
                    "categories": ", ".join(readable_types),
                    "price_level": price_map.get(price_level, "") if price_level is not None else "",
                    "description": editorial.get("overview", ""),
                    # Services proposés
                    "dine_in": detail.get("dine_in", ""),
                    "takeout": detail.get("takeout", ""),
                    "delivery": detail.get("delivery", ""),
                    "reservable": detail.get("reservable", ""),
                    "serves_breakfast": detail.get("serves_breakfast", ""),
                    "serves_brunch": detail.get("serves_brunch", ""),
                    "serves_lunch": detail.get("serves_lunch", ""),
                    "serves_dinner": detail.get("serves_dinner", ""),
                    "serves_beer": detail.get("serves_beer", ""),
                    "serves_wine": detail.get("serves_wine", ""),
                    "serves_vegetarian_food": detail.get("serves_vegetarian_food", ""),
                    "wheelchair_accessible": detail.get("wheelchair_accessible_entrance", ""),
                    # Note & avis
                    "rating": detail.get("rating", ""),
                    "total_reviews": detail.get("user_ratings_total", ""),
                    "customer_reviews": json.dumps(customer_reviews, ensure_ascii=False),
                    # Horaires
                    "opening_hours": " | ".join(hours),
                    "open_now": opening.get("open_now", ""),
                    # Ambiance (analyse Claude vision)
                    "photos_analysed": len(photos_bytes),
                    "ambiance_style": ambiance,
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
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Erreur : variable d'environnement ANTHROPIC_API_KEY non définie.")

    print("Collecte des restaurants parisiens sans site internet…")
    restaurants = collect_restaurants(max_per_zone=60)

    print(f"\n{'='*50}")
    print(f"Total trouvé : {len(restaurants)} restaurant(s) sans site web")

    save_results(restaurants)


if __name__ == "__main__":
    main()
