"""Point d'entrée unique du pipeline (Windows, macOS, Linux).

    python pipeline.py all                       # ingest + core
    python pipeline.py ingest
    python pipeline.py core
    python pipeline.py reload --month 2024_03    # rejoue un mois de règlements
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from ingestion import load_raw

ROOT = Path(__file__).resolve().parent
DB = str(ROOT / "boreal.duckdb")
SOURCES = ROOT / "data" / "sources"


def run_sql_dir(folder: str) -> None:
    con = duckdb.connect(DB)
    for f in sorted((ROOT / "sql" / folder).glob("*.sql")):
        print(f"[SQL] {folder}/{f.name}")
        con.execute(f.read_text(encoding="utf-8"))
    con.close()


def ingest() -> None:
    if load_raw.run(DB, SOURCES) != 0:
        sys.exit("Ingestion en échec : voir meta.ingestion_log")


def reload(month: str) -> None:
    rc = load_raw.run(DB, SOURCES, only=f"reglements/reglements_{month}.csv", force=True)
    if rc != 0:
        sys.exit("Rechargement en échec : voir meta.ingestion_log")
    run_sql_dir("core")


STEPS = {
    "ingest": ingest,
    "core": lambda: run_sql_dir("core"),
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["all", "reload", *STEPS])
    ap.add_argument("--month", help="AAAA_MM pour reload")
    a = ap.parse_args()
    if a.step == "all":
        for name in ["ingest", "core"]:
            STEPS[name]()
    elif a.step == "reload":
        if not a.month:
            sys.exit("Usage : python pipeline.py reload --month AAAA_MM")
        reload(a.month)
    else:
        STEPS[a.step]()
