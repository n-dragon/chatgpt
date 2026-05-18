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


def _build_services_text(r: dict) -> str:
    lines = []
    if r.get("dine_in") is True:    lines.append("Sur place")
    if r.get("takeout") is True:    lines.append("À emporter")
    if r.get("delivery") is True:   lines.append("Livraison")
    if r.get("reservable") is True: lines.append("Réservation possible")
    meals = []
    if r.get("serves_breakfast"): meals.append("petit-déjeuner")
    if r.get("serves_brunch"):    meals.append("brunch")
    if r.get("serves_lunch"):     meals.append("déjeuner")
    if r.get("serves_dinner"):    meals.append("dîner")
    if meals:
        lines.append("Service : " + ", ".join(meals))
    extras = []
    if r.get("serves_beer"):             extras.append("bière")
    if r.get("serves_wine"):             extras.append("vin")
    if r.get("serves_vegetarian_food"):  extras.append("plats végétariens")
    if extras:
        lines.append("Propose : " + ", ".join(extras))
    return " · ".join(lines)


def generate_website(restaurant: dict, photos_bytes: list[bytes], output_dir: str = "websites") -> str:
    """
    Génère une page HTML one-page pour le restaurant via Claude (vision + génération).
    Sauvegarde le fichier dans output_dir et retourne le chemin relatif.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Prépare les blocs images pour Claude
    content: list[dict] = []
    for raw in photos_bytes:
        b64 = base64.standard_b64encode(raw).decode("utf-8")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })

    # Reconstruit les avis lisibles
    try:
        reviews_list = json.loads(restaurant.get("customer_reviews", "[]"))
        reviews_txt = "\n".join(
            f'  • {rv["author"]} ({rv["rating"]}/5, {rv["time"]}) : '
            f'"{rv["text"][:220].strip()}"'
            for rv in reviews_list[:3] if rv.get("text")
        )
    except Exception:
        reviews_txt = "  Aucun avis disponible."

    # Photographies en data-URI pour l'insertion dans le HTML
    photos_data_uris = [
        "data:image/jpeg;base64," + base64.standard_b64encode(raw).decode("utf-8")
        for raw in photos_bytes
    ]
    photos_vars = "\n".join(
        f'  PHOTO_{i + 1} = "{uri[:60]}…"  ({len(raw) // 1024} Ko)'
        for i, (uri, raw) in enumerate(zip(photos_data_uris, photos_bytes))
    )

    services = _build_services_text(restaurant)

    prompt = f"""Tu es un designer web expert. Génère une page HTML one-page complète pour ce restaurant parisien.

━━━━━━━━━━━━ DONNÉES DU RESTAURANT ━━━━━━━━━━━━
Nom          : {restaurant["name"]}
Adresse      : {restaurant["address"]}
Téléphone    : {restaurant["phone"] or "Non renseigné"}
Google Maps  : {restaurant["google_maps_url"]}
Catégories   : {restaurant["categories"]}
Prix         : {restaurant["price_level"] or "Non renseigné"}
Note         : {restaurant["rating"]}/5 ({restaurant["total_reviews"]} avis)
Statut       : {restaurant["business_status"]}

DESCRIPTION GOOGLE :
{restaurant["description"] or "Aucune description disponible."}

AMBIANCE & STYLE (analyse visuelle des photos) :
{restaurant["ambiance_style"] or "Aucune analyse disponible."}

HORAIRES :
{restaurant["opening_hours"].replace(" | ", chr(10) + "  ") if restaurant["opening_hours"] else "Non renseignés"}

SERVICES :
{services or "Non renseignés"}

AVIS CLIENTS :
{reviews_txt}

━━━━━━━━━━━━ PHOTOS DISPONIBLES ━━━━━━━━━━━━
{f"Ci-jointes : {len(photos_bytes)} photo(s) du restaurant (utilisées pour le hero et la galerie)." if photos_bytes else "Aucune photo disponible."}
{photos_vars}

━━━━━━━━━━━━ INSTRUCTIONS DE GÉNÉRATION ━━━━━━━━━━━━
1. STYLE : le design doit être 100 % cohérent avec l'ambiance du restaurant déduite des photos et de la description. Sois radical dans tes choix graphiques : un bistrot chaleureux ≠ un gastronomique épuré ≠ une cantine asiatique vibrante. Couleurs, typographies, espacements, tout doit coller à l'identité.

2. STRUCTURE OBLIGATOIRE (dans cet ordre) :
   a) Section HERO pleine largeur — nom du restaurant en grand, sous-titre accrocheur, photo principale en arrière-plan ou en vedette.
   b) Section À PROPOS — présentation du restaurant (utilise description + ambiance), services, gamme de prix.
   c) Section MENU SUGGÉRÉ — propose un menu réaliste et attrayant en cohérence avec le type de cuisine et le niveau de prix. Minimum 3 catégories (Entrées, Plats, Desserts) avec 3-4 items chacune incluant un prix cohérent. Si restaurant asiatique → items asiatiques, si bistrot → plats de brasserie, etc. Présente-le visuellement (grille, cartes, typo élégante).
   d) Section HORAIRES — tableau ou liste visuelle des jours/heures.
   e) Section CONTACT — adresse, téléphone, bouton « Itinéraire » (lien vers Google Maps fourni ci-dessus).

3. PHOTOS : si des photos sont disponibles, intègre-les dans le HTML en utilisant exactement les data URIs fournis ci-dessous (ne les tronque pas, copie-les intégralement). Photo principale dans le hero, les autres dans une galerie ou section dédiée.

4. TECHNIQUE :
   - HTML5 + CSS entièrement inline dans une balise <style>
   - Google Fonts via CDN autorisé (choisis une fonte adaptée au style)
   - Responsive (flexbox ou grid, breakpoints 768px minimum)
   - Animations CSS subtiles si appropriées au style
   - Aucune dépendance JS externe
   - Les images sont déjà en base64 dans le code, pas besoin d'URL externe

5. FORMAT DE RÉPONSE : retourne UNIQUEMENT le code HTML complet (de <!DOCTYPE html> à </html>), sans bloc markdown, sans explication.

━━━━━━━━━━━━ DATA URIs DES PHOTOS ━━━━━━━━━━━━
{chr(10).join(f'PHOTO_{i + 1} (utilise en src de <img>) : {uri}' for i, uri in enumerate(photos_data_uris)) if photos_data_uris else "Aucune photo."}
"""

    content.append({"type": "text", "text": prompt})

    html = ""
    try:
        with ANTHROPIC_CLIENT.messages.stream(
            model="claude-opus-4-7",
            max_tokens=16000,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            html = stream.get_final_message().content[0].text.strip()

        # Retire les éventuelles balises markdown
        if html.startswith("```"):
            html = "\n".join(html.split("\n")[1:])
        if html.endswith("```"):
            html = html.rsplit("```", 1)[0].strip()
    except Exception as exc:
        print(f"    [claude] erreur génération site : {exc}")
        return ""

    # Sauvegarde du fichier
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in restaurant["name"])
    safe_name = safe_name.strip().replace(" ", "_")[:60]
    filename = f"{safe_name}_{restaurant['place_id'][-8:]}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"    [site] {filepath}")
    return filepath


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

                name = detail.get("name", place.get("name", ""))
                ambiance = analyze_ambiance(name, photos_bytes)

                restaurant = {
                    # Identité
                    "place_id": place_id,
                    "name": name,
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
                    # Site généré
                    "website_file": "",
                }

                # Génération du site one-page
                website_path = generate_website(restaurant, photos_bytes)
                restaurant["website_file"] = website_path

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
    print("Pour chaque restaurant : analyse ambiance + génération site HTML\n")
    restaurants = collect_restaurants(max_per_zone=60)

    print(f"\n{'='*50}")
    print(f"Total trouvé  : {len(restaurants)} restaurant(s) sans site web")
    sites = [r for r in restaurants if r.get("website_file")]
    print(f"Sites générés : {len(sites)} (dossier : websites/)")

    save_results(restaurants)


if __name__ == "__main__":
    main()
