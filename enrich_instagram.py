"""
Enrichit results.json avec les URLs Instagram des restaurants déjà collectés.

Prérequis :
    pip install duckduckgo-search

Usage :
    python enrich_instagram.py
    python enrich_instagram.py --dry-run   # affiche sans sauvegarder
"""

import re
import csv
import json
import time
import argparse

from ddgs import DDGS


def find_instagram(restaurant_name: str) -> str:
    query = f'"{restaurant_name}" Paris site:instagram.com'
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=5):
                url = result.get("href", "")
                if "instagram.com/" in url:
                    match = re.search(r"instagram\.com/([^/?#]+)", url)
                    if match and match.group(1) not in ("p", "reel", "stories", "explore", "accounts"):
                        return f"https://www.instagram.com/{match.group(1)}/"
    except Exception as exc:
        print(f"  [erreur] {exc}")
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json",    default="results.json")
    parser.add_argument("--csv",     default="results.csv")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--redo",    action="store_true", help="Recherche même si déjà renseigné")
    args = parser.parse_args()

    with open(args.json, encoding="utf-8") as f:
        restaurants = json.load(f)

    to_enrich = [
        r for r in restaurants
        if not r.get("instagram_url") or args.redo
    ]
    print(f"{len(to_enrich)} restaurants à enrichir sur {len(restaurants)} total\n")

    found = 0
    for r in to_enrich:
        name = r["name"]
        print(f"  {name} ...", end=" ", flush=True)

        if args.dry_run:
            print("[dry-run]")
            continue

        url = find_instagram(name)
        r["instagram_url"] = url
        if url:
            print(url)
            found += 1
        else:
            print("—")

        time.sleep(1.5)  # évite le rate limit DuckDuckGo

    if args.dry_run:
        print("\nDry-run — rien n'a été sauvegardé.")
        return

    # Sauvegarde JSON
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(restaurants, f, ensure_ascii=False, indent=2)

    # Sauvegarde CSV
    fieldnames = list(restaurants[0].keys())
    for col in ("instagram_url", "netlify_url", "email"):
        if col not in fieldnames:
            fieldnames.append(col)
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in restaurants:
            writer.writerow({**r, "instagram_url": r.get("instagram_url", ""),
                             "netlify_url": r.get("netlify_url", ""),
                             "email": r.get("email", "")})

    print(f"\n{'='*40}")
    print(f"Instagram trouvé : {found} / {len(to_enrich)}")
    print(f"results.json + results.csv mis à jour")


if __name__ == "__main__":
    main()
