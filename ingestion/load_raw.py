"""Chargement des sources dans la couche brute (schéma raw).

- Aucune transformation de valeur : tout est stocké en texte, tel que lu.
- Chaque ligne porte _source_file, _row_number, _loaded_at.
- Les colonnes sont alignées par nom (alias : montant_eur -> montant).
- Encodage et séparateur détectés automatiquement.
- Idempotent : un fichier déjà chargé avec le même hash est ignoré ;
  un fichier rechargé (--force) voit ses lignes supprimées puis réinsérées.
- Chaque fichier est tracé dans meta.ingestion_log.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

# Colonnes attendues par table brute (contrat de données)
SOURCES = {
    "clients": {
        "pattern": "crm/clients*.csv",
        "columns": ["client_id", "date_naissance", "region", "csp", "consent_marketing", "email_hash"],
    },
    "contrats": {
        "pattern": "contrats/contrats*.csv",
        "columns": ["contrat_id", "client_id", "produit", "date_effet", "date_resiliation", "formule",
                    "canal_distribution", "zone_risque", "franchise", "bonus_malus", "puissance_cv",
                    "surface_m2", "prime_annuelle"],
    },
    "sinistres": {
        "pattern": "sinistres/sinistres*.jsonl",
        "columns": ["sinistre_id", "contrat_id", "date_survenance", "date_declaration", "garantie",
                    "statut", "reserve_initiale"],
    },
    "reglements": {
        "pattern": "reglements/reglements_*.csv",
        "columns": ["paiement_id", "sinistre_id", "date_paiement", "montant"],
    },
    "audits": {
        "pattern": "antifraude/audits*.csv",
        "columns": ["sinistre_id", "date_audit", "fraude_confirmee"],
    },
}

# Variantes de noms de colonnes rencontrées dans les livraisons
ALIASES = {
    "montant_eur": "montant",
}

META_COLS = ["_source_file", "_row_number", "_loaded_at"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1"), "latin-1"


def normalise(col: str) -> str:
    c = col.strip().lower()
    return ALIASES.get(c, c)


def read_csv(path: Path) -> tuple[pd.DataFrame, int, list[dict]]:
    text, _ = decode(path.read_bytes())
    sample = text[:5000]
    try:
        sep = csv.Sniffer().sniff(sample, delimiters=",;|\t").delimiter
    except csv.Error:
        sep = ","
    reader = csv.reader(io.StringIO(text), delimiter=sep)
    header = [normalise(c) for c in next(reader)]
    rows, rejects, n = [], [], 0
    for i, rec in enumerate(reader, start=1):
        if not rec or all(v.strip() == "" for v in rec):
            continue
        n += 1
        if len(rec) != len(header):
            rejects.append({"line": i, "content": sep.join(rec), "motif": f"{len(rec)} champs au lieu de {len(header)}"})
            continue
        rows.append([v if v != "" else None for v in rec] + [i])
    df = pd.DataFrame(rows, columns=header + ["_row_number"], dtype="object")
    return df, n, rejects


def read_jsonl(path: Path) -> tuple[pd.DataFrame, int, list[dict]]:
    text, _ = decode(path.read_bytes())
    rows, rejects, n = [], [], 0
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        n += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            rejects.append({"line": i, "content": line[:500], "motif": f"JSON invalide : {e.msg}"})
            continue
        rec = {normalise(k): (None if v is None else str(v)) for k, v in obj.items()}
        rec["_row_number"] = i
        rows.append(rec)
    return pd.DataFrame(rows, dtype="object"), n, rejects


def init(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")
    con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")
    for table, spec in SOURCES.items():
        cols = ", ".join(f"{c} VARCHAR" for c in spec["columns"])
        con.execute(f"""CREATE TABLE IF NOT EXISTS raw.{table} (
            {cols}, _source_file VARCHAR, _row_number INTEGER, _loaded_at TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS meta.ingestion_log (
        run_id VARCHAR, source VARCHAR, fichier VARCHAR, hash VARCHAR,
        lignes_lues INTEGER, lignes_chargees INTEGER, lignes_rejetees INTEGER,
        duree_s DOUBLE, statut VARCHAR, message VARCHAR, horodatage TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS quarantine.raw_rejets (
        fichier VARCHAR, ligne INTEGER, contenu VARCHAR, motif VARCHAR, _loaded_at TIMESTAMP)""")


def already_loaded(con, fichier: str, h: str) -> bool:
    r = con.execute("""SELECT hash FROM meta.ingestion_log
        WHERE fichier = ? AND statut = 'OK' ORDER BY horodatage DESC LIMIT 1""", [fichier]).fetchone()
    return r is not None and r[0] == h


def load_file(con, run_id: str, table: str, spec: dict, path: Path, rel: str, force: bool) -> str:
    t0 = time.perf_counter()
    h = sha256(path)
    now = datetime.now()
    if not force and already_loaded(con, rel, h):
        con.execute("INSERT INTO meta.ingestion_log VALUES (?,?,?,?,0,0,0,?, 'SKIPPED', 'déjà chargé (même hash)', ?)",
                    [run_id, table, rel, h, time.perf_counter() - t0, now])
        return "SKIPPED"
    try:
        df, n_read, rejects = (read_jsonl if path.suffix == ".jsonl" else read_csv)(path)
        missing = [c for c in spec["columns"] if c not in df.columns]
        extra = [c for c in df.columns if c not in spec["columns"] + ["_row_number"]]
        if missing or extra:
            raise ValueError(f"structure inattendue : manquantes={missing} en trop={extra}")
        df = df[spec["columns"] + ["_row_number"]].copy()
        df["_source_file"] = rel
        df["_loaded_at"] = now
        con.execute("BEGIN")
        # rechargement idempotent : on retire d'abord ce que ce fichier avait apporté
        con.execute(f"DELETE FROM raw.{table} WHERE _source_file = ?", [rel])
        con.execute("DELETE FROM quarantine.raw_rejets WHERE fichier = ?", [rel])
        con.register("incoming", df)
        con.execute(f"INSERT INTO raw.{table} BY NAME SELECT * FROM incoming")
        con.unregister("incoming")
        for r in rejects:
            con.execute("INSERT INTO quarantine.raw_rejets VALUES (?,?,?,?,?)",
                        [rel, r["line"], r["content"], r["motif"], now])
        con.execute("INSERT INTO meta.ingestion_log VALUES (?,?,?,?,?,?,?,?, 'OK', NULL, ?)",
                    [run_id, table, rel, h, n_read, len(df), len(rejects), time.perf_counter() - t0, now])
        con.execute("COMMIT")
        return "OK"
    except Exception as e:  # noqa: BLE001
        try:
            con.execute("ROLLBACK")
        except Exception:  # noqa: BLE001
            pass
        con.execute("INSERT INTO meta.ingestion_log VALUES (?,?,?,?,NULL,NULL,NULL,?, 'FAILED', ?, ?)",
                    [run_id, table, rel, h, time.perf_counter() - t0, str(e)[:500], now])
        return "FAILED"


def run(db: str, sources: Path, only: str | None = None, force: bool = False) -> int:
    con = duckdb.connect(db)
    init(con)
    run_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    failed = 0
    for table, spec in SOURCES.items():
        for path in sorted(sources.glob(spec["pattern"])):
            rel = path.relative_to(sources).as_posix()
            if only and not fnmatch.fnmatch(rel, only):
                continue
            status = load_file(con, run_id, table, spec, path, rel, force)
            failed += status == "FAILED"
            if status != "SKIPPED":
                print(f"[{status:7}] {rel}")
    summary = con.execute("""SELECT statut, count(*) FROM meta.ingestion_log
        WHERE run_id = ? GROUP BY statut ORDER BY statut""", [run_id]).fetchall()
    print("Résumé :", dict(summary))
    con.close()
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="boreal.duckdb")
    ap.add_argument("--sources", default="data/sources")
    ap.add_argument("--only", help="motif de fichier, ex. 'reglements/reglements_2024_03.csv'")
    ap.add_argument("--force", action="store_true", help="recharge même si le hash est identique")
    a = ap.parse_args()
    sys.exit(run(a.db, Path(a.sources), a.only, a.force))
