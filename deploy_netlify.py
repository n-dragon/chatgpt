"""
Déploie sur Netlify tous les sites HTML déjà générés dans websites/
et met à jour results.json + results.csv avec les URLs obtenues.

Prérequis :
    pip install requests certifi

Usage :
    export NETLIFY_TOKEN="ton_token_netlify"   # Windows : set NETLIFY_TOKEN=...
    python deploy_netlify.py
    python deploy_netlify.py --dry-run   # aperçu sans déployer
"""

import io
import os
import re
import csv
import json
import time
import zipfile
import argparse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False

NETLIFY_TOKEN = os.environ.get("NETLIFY_TOKEN")
NETLIFY_API   = "https://api.netlify.com/api/v1"


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = slug.replace("'", "").replace("’", "")
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]",   "e", slug)
    slug = re.sub(r"[ìíîï]",   "i", slug)
    slug = re.sub(r"[òóôõö]",  "o", slug)
    slug = re.sub(r"[ùúûü]",   "u", slug)
    slug = re.sub(r"[ç]",      "c", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:50]


def deploy_site(name: str, place_id: str, html_path: str) -> str:
    """Crée un site Netlify et y déploie le fichier HTML. Retourne l'URL."""
    auth = {"Authorization": f"Bearer {NETLIFY_TOKEN}"}
    slug = _slugify(name)

    # Création du site (essai slug simple, puis avec suffixe place_id)
    site_id = site_name = None
    for candidate in [slug, f"{slug}-{place_id[-6:].lower()}"]:
        resp = requests.post(
            f"{NETLIFY_API}/sites",
            headers={**auth, "Content-Type": "application/json"},
            json={"name": candidate},
            timeout=15,
            verify=SSL_VERIFY,
        )
        if resp.status_code in (200, 201):
            site_id   = resp.json()["id"]
            site_name = resp.json()["name"]
            break

    if not site_id:
        print(f"  [ERREUR] impossible de créer le site pour « {name} » — réponse : {resp.status_code} {resp.text[:200]}")
        return ""

    # Empaquetage HTML → ZIP en mémoire
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_content)
    buf.seek(0)

    # Déploiement (retry automatique si rate limit 429)
    zip_data = buf.read()
    for attempt in range(4):
        deploy = requests.post(
            f"{NETLIFY_API}/sites/{site_id}/deploys",
            headers={**auth, "Content-Type": "application/zip"},
            data=zip_data,
            timeout=60,
            verify=SSL_VERIFY,
        )
        if deploy.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"  [rate limit] attente {wait}s...", end=" ", flush=True)
            time.sleep(wait)
            continue
        break

    if deploy.status_code not in (200, 201):
        print(f"  [ERREUR] déploiement {name} : {deploy.status_code} {deploy.text[:200]}")
        return ""

    return f"https://{site_name}.netlify.app"


def main():
    parser = argparse.ArgumentParser(description="Déploie les sites générés sur Netlify")
    parser.add_argument("--json",    default="results.json", help="Fichier JSON source")
    parser.add_argument("--csv",     default="results.csv",  help="Fichier CSV à mettre à jour")
    parser.add_argument("--dry-run", action="store_true",    help="Affiche sans déployer")
    args = parser.parse_args()

    if not NETLIFY_TOKEN and not args.dry_run:
        raise SystemExit(
            "Erreur : variable NETLIFY_TOKEN non définie.\n"
            "  export NETLIFY_TOKEN='ton_token_netlify'"
        )

    with open(args.json, encoding="utf-8") as f:
        restaurants = json.load(f)

    # Sélectionne ceux qui ont un fichier HTML mais pas encore d'URL Netlify
    to_deploy = [
        r for r in restaurants
        if r.get("website_file") and os.path.exists(r["website_file"])
        and not r.get("netlify_url")
    ]
    already = sum(1 for r in restaurants if r.get("netlify_url"))

    print(f"{len(restaurants)} restaurants au total")
    print(f"  → {already} déjà déployés sur Netlify")
    print(f"  → {len(to_deploy)} à déployer\n")

    deployed = 0
    for r in to_deploy:
        name      = r["name"]
        place_id  = r["place_id"]
        html_path = r["website_file"]

        if args.dry_run:
            print(f"[DRY-RUN] {name}  →  {html_path}")
            continue

        print(f"Déploiement : {name} ...", end=" ", flush=True)
        url = deploy_site(name, place_id, html_path)
        if url:
            r["netlify_url"] = url
            print(url)
            deployed += 1
        else:
            print("échec")

        time.sleep(3)  # Netlify : max ~20 déploiements/minute

    if args.dry_run:
        print(f"\nDry-run terminé — relance sans --dry-run pour déployer.")
        return

    # Sauvegarde JSON mis à jour
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(restaurants, f, ensure_ascii=False, indent=2)

    # Sauvegarde CSV mis à jour
    if restaurants:
        fieldnames = list(restaurants[0].keys())
        for col in ("netlify_url", "email"):
            if col not in fieldnames:
                fieldnames.append(col)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in restaurants:
                writer.writerow({**r, "email": r.get("email", ""), "netlify_url": r.get("netlify_url", "")})

    print(f"\n{'='*40}")
    print(f"Déployés : {deployed}  |  JSON + CSV mis à jour")
    print("\nURLs générées :")
    for r in restaurants:
        if r.get("netlify_url"):
            print(f"  {r['name']:40s}  {r['netlify_url']}")


if __name__ == "__main__":
    main()
