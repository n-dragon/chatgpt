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

import io
import os
import re
import time
import json
import csv
import base64
import zipfile
import requests
import anthropic

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
NETLIFY_TOKEN = os.environ.get("NETLIFY_TOKEN")
ANTHROPIC_CLIENT = anthropic.Anthropic()

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"
NETLIFY_API = "https://api.netlify.com/api/v1"

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


def build_photo_url(photo_reference: str, max_width: int = 800) -> str:
    """Retourne l'URL Places Photos pour une référence (le navigateur suit la redirection 302)."""
    return (
        f"{PLACES_PHOTO_URL}?maxwidth={max_width}"
        f"&photo_reference={photo_reference}&key={API_KEY}"
    )


def fetch_photo_bytes(photo_reference: str, max_width: int = 800) -> bytes | None:
    """
    Tente de télécharger les octets d'une photo Google Maps.
    Retourne None si le CDN bloque la requête (403 courant hors navigateur).
    """
    params = {
        "maxwidth": max_width,
        "photo_reference": photo_reference,
        "key": API_KEY,
    }
    try:
        resp = requests.get(
            PLACES_PHOTO_URL, params=params, allow_redirects=False, timeout=10
        )
        redirect_url = resp.headers.get("Location")
        if redirect_url:
            # Les CDN lh3.googleusercontent.com bloquent souvent les requêtes hors navigateur
            img_resp = requests.get(redirect_url, timeout=10)
            if img_resp.status_code == 200:
                return img_resp.content
        elif resp.status_code == 200:
            return resp.content
    except Exception:
        pass
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


def _slugify(name: str) -> str:
    """Convertit un nom de restaurant en slug URL-friendly."""
    slug = name.lower().strip()
    slug = slug.replace("'", "").replace("'", "")
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")[:50]
    return slug


def deploy_to_netlify(restaurant_name: str, place_id: str, html_content: str) -> str:
    """
    Déploie le HTML sur Netlify et retourne l'URL publique.
    Nécessite la variable d'environnement NETLIFY_TOKEN.
    """
    if not NETLIFY_TOKEN:
        return ""

    auth_headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}"}
    slug = _slugify(restaurant_name)

    # Création du site (essai avec le slug, puis avec suffixe place_id si pris)
    for candidate in [slug, f"{slug}-{place_id[-6:].lower()}"]:
        resp = requests.post(
            f"{NETLIFY_API}/sites",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"name": candidate},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            site_id = resp.json()["id"]
            site_name = resp.json()["name"]
            break
    else:
        print(f"    [netlify] impossible de créer le site pour {restaurant_name}")
        return ""

    # Empaquetage HTML → ZIP en mémoire
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_content)
    buf.seek(0)

    # Déploiement
    deploy_resp = requests.post(
        f"{NETLIFY_API}/sites/{site_id}/deploys",
        headers={**auth_headers, "Content-Type": "application/zip"},
        data=buf.read(),
        timeout=60,
    )
    if deploy_resp.status_code not in (200, 201):
        print(f"    [netlify] erreur déploiement : {deploy_resp.status_code} {deploy_resp.text[:200]}")
        return ""

    return f"https://{site_name}.netlify.app"


def generate_website(
    restaurant: dict,
    photos_bytes: list[bytes],
    photo_urls: list[str] | None = None,
    output_dir: str = "websites",
) -> tuple[str, str]:
    """
    Génère une page HTML one-page pour le restaurant via Claude.
    Si des octets de photos sont disponibles, ils sont envoyés à Claude (vision).
    Les URLs photos sont intégrées dans le HTML en <img src> pour un affichage navigateur.
    Retourne (chemin_fichier_local, url_netlify).
    """
    os.makedirs(output_dir, exist_ok=True)
    if photo_urls is None:
        photo_urls = []

    # Prépare les blocs images pour Claude (vision) si disponibles
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

    photos_vars = ""  # Les URLs sont listées séparément dans le prompt

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
{f"{len(photo_urls)} URL(s) photo Google Maps à intégrer directement en src= des balises <img>." if photo_urls else "Aucune photo disponible."}
{photos_vars}

━━━━━━━━━━━━ INSTRUCTIONS DE GÉNÉRATION ━━━━━━━━━━━━
1. STYLE : le design doit être 100 % cohérent avec l'ambiance du restaurant déduite des photos et de la description. Sois radical dans tes choix graphiques : un bistrot chaleureux ≠ un gastronomique épuré ≠ une cantine asiatique vibrante. Couleurs, typographies, espacements, tout doit coller à l'identité.

2. STRUCTURE OBLIGATOIRE (dans cet ordre) :
   a) Section HERO pleine largeur — nom du restaurant en grand, sous-titre accrocheur, photo principale en arrière-plan ou en vedette.
   b) Section À PROPOS — présentation du restaurant (utilise description + ambiance), services, gamme de prix.
   c) Section MENU SUGGÉRÉ — propose un menu réaliste et attrayant en cohérence avec le type de cuisine et le niveau de prix. Minimum 3 catégories (Entrées, Plats, Desserts) avec 3-4 items chacune incluant un prix cohérent. Si restaurant asiatique → items asiatiques, si bistrot → plats de brasserie, etc. Présente-le visuellement (grille, cartes, typo élégante).
   d) Section HORAIRES — tableau ou liste visuelle des jours/heures.
   e) Section CONTACT — adresse, téléphone, bouton « Itinéraire » (lien vers Google Maps fourni ci-dessus).

3. PHOTOS : intègre les URLs fournies ci-dessous directement dans les balises <img src="URL"> (le navigateur affichera les photos automatiquement via la redirection Google). Photo principale dans le hero en background-image ou <img>, les autres dans une galerie. Ajoute un attribut onerror="this.style.display='none'" sur chaque <img> au cas où une URL expirerait.

4. TECHNIQUE :
   - HTML5 + CSS entièrement inline dans une balise <style>
   - Google Fonts via CDN autorisé (choisis une fonte adaptée au style)
   - Responsive (flexbox ou grid, breakpoints 768px minimum)
   - Animations CSS subtiles si appropriées au style
   - Aucune dépendance JS externe

5. FORMAT DE RÉPONSE : retourne UNIQUEMENT le code HTML complet (de <!DOCTYPE html> à </html>), sans bloc markdown, sans explication.

━━━━━━━━━━━━ URLs DES PHOTOS (utilise en src= de <img>) ━━━━━━━━━━━━
{chr(10).join(f'PHOTO_{i + 1} : {url}' for i, url in enumerate(photo_urls)) if photo_urls else "Aucune photo."}
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
        return "", ""

    # Sauvegarde du fichier
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in restaurant["name"])
    safe_name = safe_name.strip().replace(" ", "_")[:60]
    filename = f"{safe_name}_{restaurant['place_id'][-8:]}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"    [site] {filepath}")

    # Déploiement Netlify si token disponible
    netlify_url = deploy_to_netlify(restaurant["name"], restaurant["place_id"], html)
    if netlify_url:
        print(f"    [netlify] {netlify_url}")

    return filepath, netlify_url


def collect_restaurants(max_per_zone: int = 60, max_zones: int | None = None) -> list[dict]:
    """
    Parcourt les arrondissements de Paris et retourne les restaurants sans site web.
    max_per_zone : nombre max de restaurants analysés par arrondissement.
    max_zones    : nombre d'arrondissements à couvrir (None = tous les 20).
    """
    seen_place_ids = set()
    results = []
    zones = PARIS_ZONES[:max_zones] if max_zones else PARIS_ZONES

    for zone in zones:
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

                # Photos → URLs directes + tentative de téléchargement pour vision Claude
                raw_photos = detail.get("photos") or []
                photo_urls = []
                photos_bytes = []
                for photo_info in raw_photos[:MAX_PHOTOS_PER_RESTAURANT]:
                    ref = photo_info.get("photo_reference", "")
                    if ref:
                        photo_urls.append(build_photo_url(ref))
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
                    "photo_urls": json.dumps(photo_urls, ensure_ascii=False),
                    "ambiance_style": ambiance,
                    # Sites générés
                    "website_file": "",
                    "netlify_url": "",
                }

                # Génération du site one-page + déploiement Netlify
                website_path, netlify_url = generate_website(
                    restaurant, photos_bytes, photo_urls=photo_urls
                )
                restaurant["website_file"] = website_path
                restaurant["netlify_url"] = netlify_url

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
        # Garantit la présence des colonnes à remplir manuellement
        for col in ("netlify_url", "email"):
            if col not in fieldnames:
                fieldnames.append(col)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in restaurants:
                row = {**r, "email": r.get("email", ""), "netlify_url": r.get("netlify_url", "")}
                writer.writerow(row)
        print(f"CSV sauvegardé  : {csv_path}")
        print(f"→ Remplis la colonne 'email' dans {csv_path} puis lance : python send_emails.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Collecte restaurants Paris sans site web")
    parser.add_argument(
        "--max-per-zone", type=int, default=60,
        help="Nombre max de restaurants à analyser par arrondissement (défaut: 60)"
    )
    parser.add_argument(
        "--zones", type=int, default=None,
        help="Nombre d'arrondissements à couvrir (défaut: tous les 20)"
    )
    args = parser.parse_args()

    if not API_KEY:
        raise SystemExit("Erreur : variable d'environnement GOOGLE_MAPS_API_KEY non définie.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Erreur : variable d'environnement ANTHROPIC_API_KEY non définie.")

    print("Collecte des restaurants parisiens sans site internet…")
    print("Pour chaque restaurant : analyse ambiance + génération site HTML\n")
    restaurants = collect_restaurants(max_per_zone=args.max_per_zone, max_zones=args.zones)

    print(f"\n{'='*50}")
    print(f"Total trouvé  : {len(restaurants)} restaurant(s) sans site web")
    sites = [r for r in restaurants if r.get("website_file")]
    print(f"Sites générés : {len(sites)} (dossier : websites/)")
    deployed = [r for r in restaurants if r.get("netlify_url")]
    if deployed:
        print(f"Déployés Netlify : {len(deployed)}")
        for r in deployed:
            print(f"  {r['name']} → {r['netlify_url']}")

    save_results(restaurants)


if __name__ == "__main__":
    main()
