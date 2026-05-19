"""
Envoie un email personnalisé à chaque restaurant dont la colonne 'email'
est remplie dans results.csv.

Prérequis :
    pip install resend

Configuration :
    export RESEND_API_KEY="re_xxxxxxxxxxxx"
    export FROM_EMAIL="toi@tondomaine.com"   # domaine vérifié sur resend.com

Usage :
    python send_emails.py
    python send_emails.py --csv results.csv --dry-run   # aperçu sans envoi
"""

import os
import csv
import time
import argparse

import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@tondomaine.com")


def build_email_html(name: str, address: str, phone: str,
                     netlify_url: str, maps_url: str) -> str:
    site_block = ""
    if netlify_url:
        site_block = f"""
    <div style="text-align:center;margin:32px 0;">
      <a href="{netlify_url}"
         style="background:#1a1a2e;color:#fff;text-decoration:none;
                padding:14px 32px;border-radius:6px;font-size:16px;
                font-weight:bold;display:inline-block;">
        Voir votre site →
      </a>
    </div>
    <p style="font-size:14px;color:#555;">
      Lien direct : <a href="{netlify_url}">{netlify_url}</a>
    </p>"""

    maps_block = ""
    if maps_url:
        maps_block = f"""
    <p style="margin-top:24px;">
      <a href="{maps_url}" style="color:#4a90d9;">Voir sur Google Maps</a>
    </p>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;color:#222;">

  <h1 style="font-size:22px;border-bottom:2px solid #eee;padding-bottom:12px;">
    Bonjour,
  </h1>

  <p>
    Nous avons remarqué que <strong>{name}</strong> ({address}) ne possède pas encore
    de site internet. Pour vous aider à gagner en visibilité, nous avons créé
    <strong>gratuitement</strong> une page web pour votre établissement.
  </p>

  <p>Elle contient :</p>
  <ul>
    <li>La présentation de votre restaurant et son ambiance</li>
    <li>Un menu suggéré adapté à votre cuisine</li>
    <li>Vos horaires d'ouverture</li>
    <li>Vos coordonnées et un lien Google Maps</li>
  </ul>

  {site_block}

  <p>
    Ce site vous appartient. Si vous souhaitez le modifier, le personnaliser
    ou obtenir un nom de domaine propre (ex : <em>restaurant-{name.lower().replace(' ','-')[:20]}.fr</em>),
    répondez simplement à cet email.
  </p>

  {maps_block}

  <hr style="margin-top:40px;border:none;border-top:1px solid #eee;">
  <p style="font-size:12px;color:#aaa;">
    Vous recevez cet email car votre restaurant apparaît sur Google Maps sans site web.
    Pour ne plus recevoir nos messages, répondez "désinscription".
  </p>

</body>
</html>"""


def send_emails(csv_path: str, dry_run: bool = False):
    if not RESEND_API_KEY:
        raise SystemExit(
            "Erreur : variable RESEND_API_KEY non définie.\n"
            "  export RESEND_API_KEY='re_xxxxxxxxxxxx'"
        )

    resend.api_key = RESEND_API_KEY

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    targets = [r for r in rows if r.get("email", "").strip()]
    print(f"{len(targets)} restaurant(s) avec email sur {len(rows)} total.\n")

    sent = 0
    skipped = 0

    for r in targets:
        email = r["email"].strip()
        name = r.get("name", "votre restaurant")
        address = r.get("address", "")
        phone = r.get("phone", "")
        netlify_url = r.get("netlify_url", "")
        maps_url = r.get("google_maps_url", "")

        subject = f"Nous avons créé un site web gratuit pour {name}"
        html = build_email_html(name, address, phone, netlify_url, maps_url)

        if dry_run:
            print(f"[DRY-RUN] → {email}  |  {name}  |  {netlify_url or '(pas de site Netlify)'}")
            skipped += 1
            continue

        try:
            resend.Emails.send({
                "from": FROM_EMAIL,
                "to": email,
                "subject": subject,
                "html": html,
            })
            print(f"[ENVOYÉ] {email}  —  {name}")
            sent += 1
        except Exception as exc:
            print(f"[ERREUR] {email}  —  {name}  :  {exc}")
            skipped += 1

        time.sleep(0.3)  # ~3 emails/seconde pour rester dans les limites Resend

    print(f"\n{'='*40}")
    if dry_run:
        print(f"Dry-run : {skipped} email(s) prêts à envoyer (relance sans --dry-run).")
    else:
        print(f"Envoyés : {sent}  |  Échecs : {skipped}")


def main():
    parser = argparse.ArgumentParser(description="Envoi emails restaurants")
    parser.add_argument("--csv", default="results.csv", help="Chemin vers le CSV (défaut: results.csv)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche sans envoyer")
    args = parser.parse_args()

    send_emails(args.csv, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
