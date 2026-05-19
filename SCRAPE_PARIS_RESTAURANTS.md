# Scraper de restaurants parisiens sans site internet

Pipeline Python qui collecte via l'API Google Maps les restaurants parisiens n'ayant pas de site web, enrichit chaque fiche avec une analyse visuelle par IA, puis génère automatiquement un site one-page HTML au style adapté à l'ambiance de chaque établissement.

---

## Vue d'ensemble

```
Google Maps Places API
        │
        ▼
  Recherche par arrondissement (1er → 20e)
        │  filtre : pas de champ "website"
        ▼
  Place Details API  ──────────────────────────────────────────────┐
  (coordonnées, horaires, services, avis, photos…)                 │
        │                                                           │
        ▼                                                           │
  Google Maps Photos API                                           │
  (téléchargement ≤ 3 photos / restaurant)                        │
        │                                                           │
        ├──► Claude vision (claude-opus-4-7)                        │
        │    → analyse ambiance & style (3-5 phrases)              │
        │                                                           │
        └──► Claude vision + génération (claude-opus-4-7)          │
             → site HTML one-page adapté au style du restaurant    │
                                                                    │
        ▼                                                           │
  results.json / results.csv  ◄──────────────────────────────────-─┘
  websites/{nom}_{id}.html (un fichier par restaurant)
```

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `paris_restaurants_no_website.py` | Script principal |
| `requirements.txt` | Dépendances Python (`requests`, `anthropic`) |
| `results.json` | Données complètes (généré à l'exécution) |
| `results.csv` | Même données en CSV (généré à l'exécution) |
| `websites/` | Sites HTML générés, un par restaurant (généré à l'exécution) |

---

## Installation & lancement

```bash
pip install -r requirements.txt

export GOOGLE_MAPS_API_KEY="votre_clé_google"
export ANTHROPIC_API_KEY="votre_clé_anthropic"
export NETLIFY_TOKEN="votre_token_netlify"   # optionnel — active le déploiement automatique

python paris_restaurants_no_website.py
# Options :
#   --max-per-zone 5   (limiter à 5 restaurants par arrondissement)
#   --zones 3          (couvrir seulement les 3 premiers arrondissements)
```

### Clés API nécessaires

| Clé | APIs requises | Obligatoire |
|---|---|---|
| Google Maps | Places API (Text Search, Place Details, Place Photos) | Oui |
| Anthropic | Messages API (vision + génération) | Oui |
| Netlify | Sites API + Deploys API | Non (désactive le déploiement) |

### Obtenir un token Netlify

1. Créer un compte sur [netlify.com](https://netlify.com)
2. User Settings → Applications → Personal access tokens → New access token

---

## Ce que le script collecte

### Données Places API (`results.json` / `results.csv`)

**Identité**
- `place_id`, `name`, `address`, `phone`, `google_maps_url`, `business_status`

**Activité**
- `categories` — types déduits (ex : `restaurant, japanese restaurant`)
- `price_level` — gamme de `€` à `€€€€`
- `description` — résumé éditorial Google

**Services** *(booléens)*
- `dine_in`, `takeout`, `delivery`, `reservable`
- `serves_breakfast`, `serves_brunch`, `serves_lunch`, `serves_dinner`
- `serves_beer`, `serves_wine`, `serves_vegetarian_food`
- `wheelchair_accessible`

**Avis & note**
- `rating`, `total_reviews`
- `customer_reviews` — JSON des 5 derniers avis (auteur, note, texte, date relative)

**Horaires**
- `opening_hours` — horaires par jour de la semaine
- `open_now` — statut au moment de l'appel

**Analyse IA**
- `photos_analysed` — nombre de photos téléchargées
- `photo_urls` — URLs Google Maps des photos (intégrées en `<img src>` dans le HTML)
- `ambiance_style` — description Claude du style et de l'ambiance (3-5 phrases en français)
- `website_file` — chemin vers le fichier HTML local généré
- `netlify_url` — URL publique déployée (ex : `https://le-chat-blanc.netlify.app`)

---

## Sites HTML générés (`websites/`)

Un fichier HTML auto-contenu par restaurant. Chaque page est :

- **Stylée en cohérence avec l'ambiance** détectée sur les photos (bistrot chaleureux, gastronomique épuré, cantine vibrante, etc.)
- **Responsive** (flexbox/grid, breakpoint 768 px)
- **Auto-contenue** (photos embarquées en base64, CSS inline, Google Fonts via CDN uniquement)

### Structure de chaque page

| Section | Contenu |
|---|---|
| **Hero** | Nom du restaurant, accroche, photo principale en arrière-plan |
| **À propos** | Description + ambiance + services + gamme de prix |
| **Menu suggéré** | 3+ catégories (Entrées / Plats / Desserts) avec items et prix réalistes selon le type de cuisine |
| **Horaires** | Tableau ou liste visuelle des jours d'ouverture |
| **Contact** | Adresse, téléphone, bouton « Itinéraire » lié à Google Maps |

---

## Architecture technique

### Fonctions principales

| Fonction | Rôle |
|---|---|
| `search_places(query, page_token)` | Recherche Text Search par arrondissement |
| `get_place_details(place_id)` | Récupère les détails complets d'un lieu |
| `fetch_photo_bytes(photo_reference)` | Télécharge une photo Google Maps (800 px max) |
| `analyze_ambiance(name, photos_bytes)` | Analyse le style/ambiance via Claude vision |
| `generate_website(restaurant, photos_bytes)` | Génère le HTML one-page via Claude et le sauvegarde |
| `collect_restaurants(max_per_zone)` | Orchestre la collecte sur les 20 arrondissements |
| `save_results(restaurants)` | Exporte JSON + CSV |

### Paramètres configurables

| Constante | Défaut | Rôle |
|---|---|---|
| `MAX_PHOTOS_PER_RESTAURANT` | `3` | Nombre de photos téléchargées par restaurant |
| `max_per_zone` | `60` | Restaurants analysés par arrondissement |

---

## Estimation des coûts API

### Par restaurant traité

| Appel | Coût indicatif |
|---|---|
| Place Details | ~0,017 $ |
| Place Photos (×3) | ~0,007 $ |
| Claude – analyse ambiance | ~0,01–0,05 $ |
| Claude – génération HTML | ~0,05–0,20 $ |
| **Total par restaurant** | **~0,08–0,27 $** |

Pour 1 000 restaurants sans site : environ **80 $ – 270 $**.
