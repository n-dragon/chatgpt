#!/usr/bin/env python3
"""
Senator Stock Tracker
---------------------
Fetches recent US senator stock trades from the Senate EFTS public API
and sends an email summary. Run manually or via cron.

Usage:
    python3 senator_tracker.py

Env vars (copy .env.example to .env and fill in):
    EMAIL_SENDER      - Gmail address used to send
    EMAIL_PASSWORD    - Gmail App Password (not your login password)
    EMAIL_RECIPIENT   - Address to receive alerts
    DAYS_BACK         - How many days back to look (default: 7)
"""

import os
import json
import smtplib
import datetime
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---------------------------------------------------------------------------
# Load config from environment (or .env file if python-dotenv is installed)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional; set env vars manually

EMAIL_SENDER    = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD  = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "")
DAYS_BACK       = int(os.environ.get("DAYS_BACK", "7"))


# ---------------------------------------------------------------------------
# 1. Fetch trades from Senate Electronic Financial Disclosures (EFTS)
# ---------------------------------------------------------------------------
EFTS_BASE = "https://efts.senate.gov/LATEST/search-index"

def fetch_senate_trades(days_back: int) -> list[dict]:
    """Return list of trade filings from the Senate EFTS API."""
    today      = datetime.date.today()
    from_date  = today - datetime.timedelta(days=days_back)

    params = {
        "q": "",
        "dateRange": "custom",
        "fromDate": from_date.isoformat(),
        "toDate": today.isoformat(),
        "results": "100",
    }
    url = EFTS_BASE + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={"User-Agent": "SenatorStockTracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    hits = data.get("hits", {}).get("hits", [])
    trades = []
    for hit in hits:
        src = hit.get("_source", {})
        trades.append({
            "senator":      src.get("first_name", "") + " " + src.get("last_name", ""),
            "senator_state":src.get("senator_state", ""),
            "filed_date":   src.get("date_received", "N/A"),
            "report_year":  src.get("report_year", "N/A"),
            "doc_url":      "https://efts.senate.gov/LATEST/search-index" + src.get("link", ""),
            "pdf_url":      "https://senate.gov" + src.get("pdf_url", ""),
        })
    return trades


# ---------------------------------------------------------------------------
# 2. Fetch individual trade transactions from senatestockwatcher.com
#    (richer data: ticker, amount, transaction type)
# ---------------------------------------------------------------------------
SSW_API = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json"
_ssw_cache: list[dict] | None = None

def fetch_ssw_trades(days_back: int) -> list[dict]:
    """Fetch senator trades from Senate Stock Watcher S3 aggregate (public)."""
    global _ssw_cache
    if _ssw_cache is None:
        req = urllib.request.Request(SSW_API, headers={"User-Agent": "SenatorStockTracker/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            _ssw_cache = json.loads(resp.read().decode())

    cutoff = datetime.date.today() - datetime.timedelta(days=days_back)
    results = []
    for tx in _ssw_cache:
        tx_date_str = tx.get("transaction_date") or tx.get("disclosure_date", "")
        try:
            tx_date = datetime.date.fromisoformat(tx_date_str[:10])
        except (ValueError, TypeError):
            continue
        if tx_date >= cutoff:
            results.append({
                "senator":      tx.get("senator", "N/A"),
                "ticker":       tx.get("ticker", "N/A"),
                "asset_name":   tx.get("asset_description", "N/A"),
                "type":         tx.get("type", "N/A"),         # Purchase / Sale
                "amount":       tx.get("amount", "N/A"),
                "tx_date":      tx_date_str,
                "disclosure":   tx.get("disclosure_date", "N/A"),
                "comment":      tx.get("comment", ""),
            })
    # Most recent first
    results.sort(key=lambda x: x["tx_date"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 3. Build HTML email
# ---------------------------------------------------------------------------
def build_html(trades: list[dict], days_back: int) -> str:
    today = datetime.date.today().isoformat()

    rows = ""
    for t in trades:
        tx_type  = t["type"].lower()
        color    = "#d4edda" if "purchase" in tx_type else "#f8d7da" if "sale" in tx_type else "#fff3cd"
        rows += f"""
        <tr style="background:{color}">
            <td style="padding:6px 10px">{t['senator']}</td>
            <td style="padding:6px 10px;font-weight:bold">{t['ticker']}</td>
            <td style="padding:6px 10px">{t['asset_name'][:60]}</td>
            <td style="padding:6px 10px">{t['type']}</td>
            <td style="padding:6px 10px">{t['amount']}</td>
            <td style="padding:6px 10px">{t['tx_date']}</td>
            <td style="padding:6px 10px">{t['disclosure']}</td>
        </tr>"""

    if not rows:
        rows = "<tr><td colspan='7' style='padding:12px;text-align:center'>Aucune transaction trouvée pour cette période.</td></tr>"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#222;max-width:900px;margin:auto">
  <h2 style="color:#1a3c6e">📊 Suivi des achats d'actions par les Sénateurs américains</h2>
  <p>Période : <strong>derniers {days_back} jours</strong> — Généré le <strong>{today}</strong></p>
  <p>Source : <a href="https://senate-stock-watcher.com">Senate Stock Watcher</a> /
     <a href="https://efts.senate.gov">Senate EFTS</a></p>

  <table border="0" cellspacing="0" cellpadding="0"
         style="border-collapse:collapse;width:100%;font-size:13px">
    <thead>
      <tr style="background:#1a3c6e;color:#fff">
        <th style="padding:8px 10px;text-align:left">Sénateur</th>
        <th style="padding:8px 10px;text-align:left">Ticker</th>
        <th style="padding:8px 10px;text-align:left">Actif</th>
        <th style="padding:8px 10px;text-align:left">Type</th>
        <th style="padding:8px 10px;text-align:left">Montant</th>
        <th style="padding:8px 10px;text-align:left">Date tx</th>
        <th style="padding:8px 10px;text-align:left">Divulgation</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <p style="margin-top:20px;font-size:12px;color:#666">
    Légende :
    <span style="background:#d4edda;padding:2px 6px">Achat</span> &nbsp;
    <span style="background:#f8d7da;padding:2px 6px">Vente</span> &nbsp;
    <span style="background:#fff3cd;padding:2px 6px">Autre</span>
  </p>
  <p style="font-size:11px;color:#999">
    Données publiques STOCK Act — Sénat des États-Unis
  </p>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# 4. Send email via Gmail SMTP
# ---------------------------------------------------------------------------
def send_email(subject: str, html_body: str):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        raise ValueError(
            "Variables d'environnement manquantes : EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT\n"
            "Copie .env.example → .env et remplis les valeurs."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
    print(f"[OK] Email envoyé à {EMAIL_RECIPIENT}")


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------
def main():
    print(f"[*] Récupération des transactions des {DAYS_BACK} derniers jours...")
    try:
        trades = fetch_ssw_trades(DAYS_BACK)
        print(f"[*] {len(trades)} transaction(s) trouvée(s).")
    except Exception as e:
        print(f"[!] Erreur lors de la récupération des données : {e}")
        trades = []

    html   = build_html(trades, DAYS_BACK)
    today  = datetime.date.today().isoformat()
    subject = f"[Senator Stock Tracker] {len(trades)} transaction(s) — {today}"

    try:
        send_email(subject, html)
    except ValueError as e:
        print(f"[!] Configuration email manquante :\n{e}")
    except Exception as e:
        print(f"[!] Erreur lors de l'envoi de l'email : {e}")


if __name__ == "__main__":
    main()
