#!/usr/bin/env python3
"""
Clusterise des requêtes SQL en N groupes selon les tables utilisées.

Format CSV attendu :
    timestamp,tables_utilisees,duree
    2026-01-01 01h01m12s,"table_a,table_b",150

Usage:
    python cluster_queries.py --csv queries.csv --clusters 5
    python cluster_queries.py --csv queries.csv --clusters 5 --output result.csv
"""

import argparse
import csv
import sys
from collections import defaultdict


def parse_duration(raw: str) -> float:
    """Convertit une durée brute (ms, s, ou nombre) en float (ms)."""
    raw = raw.strip().lower()
    if raw.endswith("ms"):
        return float(raw[:-2])
    if raw.endswith("s"):
        return float(raw[:-1]) * 1000
    return float(raw)


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
            rows.append({
                "timestamp": row[col_ts].strip(),
                "tables": frozenset(tables),
                "tables_list": sorted(tables),
                "duree": parse_duration(row[col_duree]),
            })
    return rows


def build_table_vectors(rows: list[dict]) -> tuple[list[str], list[list[int]]]:
    """Construit une matrice binaire (présence/absence de chaque table)."""
    all_tables = sorted({t for r in rows for t in r["tables"]})
    table_index = {t: i for i, t in enumerate(all_tables)}
    vectors = []
    for row in rows:
        vec = [0] * len(all_tables)
        for t in row["tables"]:
            vec[table_index[t]] = 1
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

def print_report(rows: list[dict], labels: list[int], all_tables: list[str], n_clusters: int):
    """Affiche un rapport détaillé par cluster."""
    clusters: dict[int, list[int]] = defaultdict(list)
    for i, lbl in enumerate(labels):
        clusters[lbl].append(i)

    print(f"\n{'='*70}")
    print(f"  RAPPORT DE CLUSTERING — {n_clusters} clusters, {len(rows)} requêtes")
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

        # Exemples de combinaisons de tables
        combos: dict[frozenset, int] = defaultdict(int)
        for i in indices:
            combos[rows[i]["tables"]] += 1
        top_combos = sorted(combos.items(), key=lambda x: -x[1])[:3]
        print(f"   Combinaisons de tables les plus courantes :")
        for combo, cnt in top_combos:
            print(f"      [{', '.join(sorted(combo))}]  x{cnt}")
        print()


def write_output_csv(path: str, rows: list[dict], labels: list[int]):
    """Écrit le CSV enrichi avec la colonne cluster."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "tables_utilisees", "duree_ms", "cluster"])
        for row, lbl in zip(rows, labels):
            writer.writerow([
                row["timestamp"],
                ",".join(row["tables_list"]),
                row["duree"],
                lbl,
            ])


def main():
    parser = argparse.ArgumentParser(
        description="Clusterise des requêtes SQL par tables utilisées."
    )
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV d'entrée")
    parser.add_argument("--clusters", "-n", type=int, default=5, help="Nombre de clusters (défaut: 5)")
    parser.add_argument("--output", "-o", help="Chemin du CSV de sortie (optionnel)")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire (défaut: 42)")
    args = parser.parse_args()

    import random
    random.seed(args.seed)

    # Chargement
    rows = load_csv(args.csv)
    if not rows:
        print("Erreur : le CSV est vide.", file=sys.stderr)
        sys.exit(1)

    n = min(args.clusters, len(rows))
    if n < args.clusters:
        print(f"Note : seulement {len(rows)} requêtes, on réduit à {n} clusters.")

    # Vectorisation + clustering
    all_tables, vectors = build_table_vectors(rows)
    print(f"Tables distinctes détectées : {len(all_tables)}")
    labels = kmeans(vectors, n)

    # Rapport
    print_report(rows, labels, all_tables, n)

    # Export
    if args.output:
        write_output_csv(args.output, rows, labels)
        print(f"Résultat exporté dans : {args.output}")


if __name__ == "__main__":
    main()
