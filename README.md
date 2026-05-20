# Restaurants parisiens sans site web

Pipeline complet qui collecte les restaurants parisiens sans site internet via Google Maps, génère un site web one-page par restaurant via Claude, déploie chaque site sur Netlify, puis contacte les propriétaires par email.

---

## Architecture

```
Google Maps API
      │
      ▼
paris_restaurants_no_website.py   ← script principal
      │
      ├─ Place Details (nom, adresse, horaires, avis, photos...)
      ├─ DuckDuckGo Search → instagram_url
      ├─ Claude vision → ambiance_style
      └─ Claude génération → HTML one-page
            │
            ├─ websites/{nom}_{id}.html   ← fichier local
            ├─ results.json               ← toutes les données
            ├─ results.csv                ← mêmes données (Excel)
            └─ Netlify API → URL dédiée par restaurant
```

---

## Fichiers

### Scripts

| Fichier | Rôle |
|---|---|
| `paris_restaurants_no_website.py` | Script principal — collecte, analyse, génération |
| `deploy_netlify.py` | Déploie les HTML existants sur Netlify (batch) |
| `enrich_instagram.py` | Enrichit results.json avec les URLs Instagram |
| `send_emails.py` | Envoie un email personnalisé à chaque restaurant |

### Données générées

| Fichier | Rôle |
|---|---|
| `results.json` | Toutes les données des restaurants (lu par le code et GitHub Pages) |
| `results.csv` | Mêmes données en tableau — à ouvrir dans Excel pour remplir les emails |
| `websites/` | Sites HTML one-page, un fichier par restaurant |

### GitHub Pages

| Fichier | Rôle |
|---|---|
| `index.html` | Page d'accueil GitHub Pages — grille searchable de tous les restaurants |
| `.nojekyll` | Désactive Jekyll pour que GitHub Pages serve les fichiers tels quels |

### Documentation

| Fichier | Rôle |
|---|---|
| `README.md` | Ce fichier |
| `SCRAPE_PARIS_RESTAURANTS.md` | Documentation détaillée du pipeline et des coûts API |

---

## Fonctionnement détaillé

### 1. Collecte (`paris_restaurants_no_website.py`)

Pour chaque arrondissement (1er → 20e) :

1. **Recherche** — Text Search API → liste de restaurants
2. **Filtre** — Place Details API → ignore ceux qui ont déjà un site web
3. **Enrichissement** pour chaque restaurant sans site :
   - Photos Google Maps (URLs directes, tentative de téléchargement)
   - Analyse d'ambiance via Claude vision (si photos disponibles)
   - Page Instagram via DuckDuckGo (`"nom" Paris site:instagram.com`)
4. **Génération HTML** — Claude génère un site one-page stylé selon l'ambiance
5. **Déploiement Netlify** — si `NETLIFY_TOKEN` défini, déploie et stocke l'URL

**Résultats sauvegardés** dans `results.json` + `results.csv` + `websites/`.

```bash
export GOOGLE_MAPS_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export NETLIFY_TOKEN="..."          # optionnel

python paris_restaurants_no_website.py
python paris_restaurants_no_website.py --max-per-zone 5 --zones 3   # test limité
```

---

### 2. Déploiement Netlify (`deploy_netlify.py`)

Déploie en batch les HTML déjà générés qui n'ont pas encore d'URL Netlify.

- Crée un site Netlify par restaurant (slug du nom en URL)
- Si le site existe déjà (422) → le récupère et redéploie dessus
- Gère le rate limit 429 via le header `Retry-After`
- Met à jour `results.json` + `results.csv` avec les URLs

```bash
export NETLIFY_TOKEN="..."
python deploy_netlify.py            # déploie les manquants
python deploy_netlify.py --redeploy # force le redéploiement de tous
python deploy_netlify.py --dry-run  # aperçu sans déployer
```

**URLs générées :** `https://le-chat-blanc.netlify.app`

---

### 3. Instagram (`enrich_instagram.py`)

Cherche la page Instagram de chaque restaurant via DuckDuckGo.

- Requête : `"nom du restaurant" Paris site:instagram.com`
- Extrait l'URL du profil (filtre les posts, reels, stories)
- Taux de réussite estimé : 40-70%
- Met à jour `results.json` + `results.csv`

```bash
pip install duckduckgo-search
python enrich_instagram.py
python enrich_instagram.py --redo   # relance même les déjà trouvés
```

---

### 4. Email (`send_emails.py`)

Envoie un email personnalisé à chaque restaurant dont la colonne `email` est remplie dans `results.csv`.

**Workflow :**
1. Ouvrir `results.csv` dans Excel
2. Remplir la colonne `email` manuellement
3. Lancer le script

```bash
export RESEND_API_KEY="re_..."
export FROM_EMAIL="toi@tondomaine.com"

python send_emails.py --dry-run     # aperçu sans envoyer
python send_emails.py               # envoi réel
```

**Contenu de l'email :**
- Annonce de la création d'un site gratuit
- Bouton → URL Netlify du restaurant
- Lien Google Maps
- Invitation à personnaliser

---

## Données collectées par restaurant

| Champ | Source | Description |
|---|---|---|
| `place_id` | Google Maps | Identifiant unique |
| `name` | Google Maps | Nom du restaurant |
| `address` | Google Maps | Adresse complète |
| `phone` | Google Maps | Numéro de téléphone |
| `google_maps_url` | Google Maps | Lien vers la fiche Maps |
| `instagram_url` | DuckDuckGo | Page Instagram (si trouvée) |
| `categories` | Google Maps | Types (bistrot, japonais…) |
| `price_level` | Google Maps | € à €€€€ |
| `rating` | Google Maps | Note /5 |
| `total_reviews` | Google Maps | Nombre d'avis |
| `customer_reviews` | Google Maps | 5 derniers avis (JSON) |
| `opening_hours` | Google Maps | Horaires par jour |
| `description` | Google Maps | Résumé éditorial Google |
| `dine_in` / `takeout` / `delivery` | Google Maps | Services proposés |
| `serves_*` | Google Maps | Repas et boissons |
| `ambiance_style` | Claude vision | Description style/ambiance |
| `photo_urls` | Google Maps | URLs des photos |
| `website_file` | Local | Chemin vers le HTML généré |
| `netlify_url` | Netlify | URL publique du site |
| `email` | Manuel | Email du propriétaire (à remplir) |

---

## Installation

```bash
git clone https://github.com/n-dragon/chatgpt.git
cd chatgpt
pip install -r requirements.txt
```

### Clés API

| Variable | Obligatoire | Obtenir |
|---|---|---|
| `GOOGLE_MAPS_API_KEY` | Oui | [console.cloud.google.com](https://console.cloud.google.com) → Places API |
| `ANTHROPIC_API_KEY` | Oui | [console.anthropic.com](https://console.anthropic.com) |
| `NETLIFY_TOKEN` | Non | app.netlify.com → User Settings → Access tokens |
| `RESEND_API_KEY` | Non (email) | [resend.com](https://resend.com) |

---

## Estimation des coûts

| Poste | Coût par restaurant | Pour 1 000 restaurants |
|---|---|---|
| Google Place Details | ~0,017 $ | ~17 $ |
| Google Place Photos (×3) | ~0,007 $ | ~7 $ |
| Claude – analyse ambiance | ~0,01–0,05 $ | ~10–50 $ |
| Claude – génération HTML | ~0,05–0,20 $ | ~50–200 $ |
| Netlify (hébergement) | Gratuit | Gratuit (< 500 sites) |
| **Total** | **~0,08–0,27 $** | **~84–274 $** |
