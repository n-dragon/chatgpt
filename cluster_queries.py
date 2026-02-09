#!/usr/bin/env python3
"""
Clusterise des requêtes SQL en N groupes selon les tables utilisées
et (optionnellement) les patterns temporels.

Format CSV attendu :
    timestamp,tables_utilisees,duree
    2026-01-01 01h01m12s,"table_a,table_b",150

Usage:
    python cluster_queries.py --csv queries.csv --clusters 5
    python cluster_queries.py --csv queries.csv --clusters 5 --temporal-weight 0.5
    python cluster_queries.py --csv queries.csv --clusters 5 --output result.csv
"""

import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from datetime import datetime


def parse_duration(raw: str) -> float:
    """Convertit une durée brute (ms, s, ou nombre) en float (ms)."""
    raw = raw.strip().lower()
    if raw.endswith("ms"):
        return float(raw[:-2])
    if raw.endswith("s"):
        return float(raw[:-1]) * 1000
    return float(raw)


def parse_timestamp(raw: str) -> datetime:
    """Parse un timestamp dans divers formats courants."""
    raw = raw.strip()
    # Format personnalisé : "2026-01-01 01h01m12s"
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2})h(\d{2})m(\d{2})s?", raw)
    if m:
        return datetime.strptime(
            f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}:{m.group(4)}",
            "%Y-%m-%d %H:%M:%S",
        )
    # Formats ISO standards
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Format de timestamp non reconnu : {raw!r}")


def extract_temporal_features(dt: datetime) -> dict:
    """Extrait des features temporelles d'un datetime.

    Retourne des features cycliques (sin/cos) pour que :
    - 23h et 1h soient proches (cycle de 24h)
    - dimanche et lundi soient proches (cycle de 7j)
    """
    hour_frac = dt.hour + dt.minute / 60.0
    dow = dt.weekday()  # 0=lundi, 6=dimanche

    return {
        "hour": hour_frac,
        "day_of_week": dow,
        "hour_sin": math.sin(2 * math.pi * hour_frac / 24),
        "hour_cos": math.cos(2 * math.pi * hour_frac / 24),
        "dow_sin": math.sin(2 * math.pi * dow / 7),
        "dow_cos": math.cos(2 * math.pi * dow / 7),
    }


def load_csv(path: str) -> list[dict]:
    """Charge le CSV et retourne une liste de dicts normalisés."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalise les noms de colonnes (strip + lowercase)
        reader.fieldnames = [c.strip().lower() for c in reader.fieldnames]

        col_ts = next((c for c in reader.fieldnames if "timestamp" in c or "date" in c), reader.fieldnames[0])
        col_tables = next((c for c in reader.fieldnames if "table" in c), reader.fieldnames[1])
        remaining = [c for c in reader.fieldnames if c not in (col_ts, col_tables)]
        col_duree = next((c for c in remaining if "dur" in c or "time" in c or "ms" in c), remaining[0] if remaining else reader.fieldnames[2])

        for row in reader:
            tables = [t.strip().lower() for t in row[col_tables].split(",") if t.strip()]
            dt = parse_timestamp(row[col_ts])
            rows.append({
                "timestamp": row[col_ts].strip(),
                "datetime": dt,
                "temporal": extract_temporal_features(dt),
                "tables": frozenset(tables),
                "tables_list": sorted(tables),
                "duree": parse_duration(row[col_duree]),
            })
    return rows


def build_feature_vectors(rows: list[dict], temporal_weight: float = 0.0
                          ) -> tuple[list[str], list[list[float]]]:
    """Construit les vecteurs de features (tables + temporel).

    Args:
        rows: liste de requêtes chargées par load_csv.
        temporal_weight: poids des features temporelles (0.0 à 1.0).
            0.0 = tables uniquement (comportement d'origine).
            1.0 = poids égal tables / temporel.
            Les features temporelles ajoutées :
              - hour_sin, hour_cos  (cycle 24h)
              - dow_sin, dow_cos    (cycle 7j)
              - duree normalisée
    """
    # --- Dimensions tables (binaire) ---
    all_tables = sorted({t for r in rows for t in r["tables"]})
    table_index = {t: i for i, t in enumerate(all_tables)}
    n_tables = len(all_tables)

    # --- Normalisation durée (min-max → [0, 1]) ---
    durees = [r["duree"] for r in rows]
    dur_min, dur_max = min(durees), max(durees)
    dur_range = dur_max - dur_min if dur_max != dur_min else 1.0

    # --- Calcul du facteur d'échelle ---
    # Les features tables sont binaires {0,1} → variance ~0.25 chacune.
    # Les features temporelles sont dans [-1,1] (sin/cos) ou [0,1] (durée).
    # On multiplie les features temporelles par `temporal_weight` ×
    # sqrt(n_tables / n_temporal_features) pour équilibrer l'influence.
    n_temporal = 5  # hour_sin, hour_cos, dow_sin, dow_cos, duree_norm
    scale = temporal_weight * math.sqrt(n_tables / n_temporal) if n_temporal > 0 else 0.0

    vectors = []
    for row in rows:
        # Partie tables
        vec = [0.0] * n_tables
        for t in row["tables"]:
            vec[table_index[t]] = 1.0

        if temporal_weight > 0:
            tf = row["temporal"]
            dur_norm = (row["duree"] - dur_min) / dur_range
            vec.extend([
                tf["hour_sin"] * scale,
                tf["hour_cos"] * scale,
                tf["dow_sin"] * scale,
                tf["dow_cos"] * scale,
                dur_norm * scale,
            ])

        vectors.append(vec)

    return all_tables, vectors


# ---------------------------------------------------------------------------
# K-Means implémenté à la main (aucune dépendance externe)
# ---------------------------------------------------------------------------

def _euclidean_sq(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _centroid(points: list[list[int]]) -> list[float]:
    n = len(points)
    if n == 0:
        return []
    dim = len(points[0])
    return [sum(p[d] for p in points) / n for d in range(dim)]


def kmeans(vectors: list[list[int]], k: int, max_iter: int = 100) -> list[int]:
    """K-Means simple. Retourne la liste des labels (un par vecteur)."""
    import random

    n = len(vectors)
    if k >= n:
        return list(range(n))

    # Initialisation K-Means++ simplifiée
    indices = [random.randrange(n)]
    for _ in range(1, k):
        dists = []
        for i, v in enumerate(vectors):
            min_d = min(_euclidean_sq(v, vectors[j]) for j in indices)
            dists.append(min_d)
        total = sum(dists)
        if total == 0:
            remaining = [i for i in range(n) if i not in indices]
            indices.append(random.choice(remaining))
            continue
        r = random.uniform(0, total)
        cumul = 0
        for i, d in enumerate(dists):
            cumul += d
            if cumul >= r:
                indices.append(i)
                break

    centroids = [list(map(float, vectors[i])) for i in indices]
    labels = [0] * n

    for _ in range(max_iter):
        # Assignation
        new_labels = []
        for v in vectors:
            best = min(range(k), key=lambda c: _euclidean_sq(v, centroids[c]))
            new_labels.append(best)

        if new_labels == labels:
            break
        labels = new_labels

        # Mise à jour des centroïdes
        groups: dict[int, list[list[int]]] = defaultdict(list)
        for i, lbl in enumerate(labels):
            groups[lbl].append(vectors[i])
        for c in range(k):
            if groups[c]:
                centroids[c] = _centroid(groups[c])

    return labels


# ---------------------------------------------------------------------------
# Rapport
# ---------------------------------------------------------------------------

HOUR_LABELS = [f"{h:02d}h" for h in range(24)]
DOW_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def _hour_histogram(indices: list[int], rows: list[dict]) -> list[int]:
    """Histogramme de requêtes par tranche horaire (0-23)."""
    hist = [0] * 24
    for i in indices:
        hist[int(rows[i]["temporal"]["hour"])] += 1
    return hist


def _dow_histogram(indices: list[int], rows: list[dict]) -> list[int]:
    """Histogramme de requêtes par jour de semaine (0=Lun, 6=Dim)."""
    hist = [0] * 7
    for i in indices:
        hist[rows[i]["temporal"]["day_of_week"]] += 1
    return hist


def _print_histogram(labels: list[str], counts: list[int], max_bar: int = 20):
    """Affiche un histogramme horizontal compact."""
    peak = max(counts) if counts else 1
    for label, count in zip(labels, counts):
        if count == 0:
            continue
        bar_len = int(count / peak * max_bar) if peak > 0 else 0
        bar = "▓" * bar_len
        print(f"      {label:4s} {bar} {count}")


def print_report(rows: list[dict], labels: list[int], all_tables: list[str],
                 n_clusters: int, show_temporal: bool = False):
    """Affiche un rapport détaillé par cluster."""
    clusters: dict[int, list[int]] = defaultdict(list)
    for i, lbl in enumerate(labels):
        clusters[lbl].append(i)

    print(f"\n{'='*70}")
    mode = "tables + temporel" if show_temporal else "tables"
    print(f"  RAPPORT DE CLUSTERING — {n_clusters} clusters, {len(rows)} requêtes ({mode})")
    print(f"{'='*70}\n")

    for c in sorted(clusters.keys()):
        indices = clusters[c]
        durees = [rows[i]["duree"] for i in indices]
        avg_dur = sum(durees) / len(durees)

        # Tables les plus fréquentes dans ce cluster
        table_freq: dict[str, int] = defaultdict(int)
        for i in indices:
            for t in rows[i]["tables"]:
                table_freq[t] += 1
        top_tables = sorted(table_freq.items(), key=lambda x: -x[1])

        print(f"── Cluster {c} ({len(indices)} requêtes) ──")
        print(f"   Durée moyenne : {avg_dur:.1f} ms")
        print(f"   Tables fréquentes :")
        for tbl, count in top_tables[:10]:
            pct = count / len(indices) * 100
            bar = "█" * int(pct / 5)
            print(f"      {tbl:30s}  {count:4d} ({pct:5.1f}%)  {bar}")

        # Combinaisons de tables les plus courantes
        combos: dict[frozenset, int] = defaultdict(int)
        for i in indices:
            combos[rows[i]["tables"]] += 1
        top_combos = sorted(combos.items(), key=lambda x: -x[1])[:3]
        print(f"   Combinaisons de tables les plus courantes :")
        for combo, cnt in top_combos:
            print(f"      [{', '.join(sorted(combo))}]  x{cnt}")

        # --- Analyse temporelle ---
        if show_temporal:
            print(f"   Distribution horaire :")
            hour_hist = _hour_histogram(indices, rows)
            _print_histogram(HOUR_LABELS, hour_hist)

            print(f"   Distribution jour de semaine :")
            dow_hist = _dow_histogram(indices, rows)
            _print_histogram(DOW_LABELS, dow_hist)

            # Plage horaire dominante
            peak_hour = max(range(24), key=lambda h: hour_hist[h])
            peak_dow = max(range(7), key=lambda d: dow_hist[d])
            print(f"   → Pic : {HOUR_LABELS[peak_hour]} | Jour dominant : {DOW_LABELS[peak_dow]}")

        print()


def write_output_csv(path: str, rows: list[dict], labels: list[int]):
    """Écrit le CSV enrichi avec la colonne cluster + features temporelles."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "tables_utilisees", "duree_ms",
                         "heure", "jour_semaine", "cluster"])
        for row, lbl in zip(rows, labels):
            writer.writerow([
                row["timestamp"],
                ",".join(row["tables_list"]),
                row["duree"],
                f"{row['temporal']['hour']:.1f}",
                DOW_LABELS[row["temporal"]["day_of_week"]],
                lbl,
            ])


def main():
    parser = argparse.ArgumentParser(
        description="Clusterise des requêtes SQL par tables utilisées et patterns temporels."
    )
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV d'entrée")
    parser.add_argument("--clusters", "-n", type=int, default=5, help="Nombre de clusters (défaut: 5)")
    parser.add_argument("--temporal-weight", "-tw", type=float, default=0.0,
                        help="Poids des features temporelles: 0.0=tables seules, "
                             "1.0=poids égal tables/temporel (défaut: 0.0)")
    parser.add_argument("--output", "-o", help="Chemin du CSV de sortie (optionnel)")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire (défaut: 42)")
    args = parser.parse_args()

    import random
    random.seed(args.seed)

    tw = max(0.0, min(1.0, args.temporal_weight))

    # Chargement
    rows = load_csv(args.csv)
    if not rows:
        print("Erreur : le CSV est vide.", file=sys.stderr)
        sys.exit(1)

    n = min(args.clusters, len(rows))
    if n < args.clusters:
        print(f"Note : seulement {len(rows)} requêtes, on réduit à {n} clusters.")

    # Vectorisation + clustering
    all_tables, vectors = build_feature_vectors(rows, temporal_weight=tw)
    print(f"Tables distinctes détectées : {len(all_tables)}")
    if tw > 0:
        print(f"Poids temporel : {tw:.2f} (features: heure cyclique, jour cyclique, durée)")
    labels = kmeans(vectors, n)

    # Rapport
    show_temporal = tw > 0
    print_report(rows, labels, all_tables, n, show_temporal=show_temporal)

    # Export
    if args.output:
        write_output_csv(args.output, rows, labels)
        print(f"Résultat exporté dans : {args.output}")


if __name__ == "__main__":
    main()
