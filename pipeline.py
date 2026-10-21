"""Point d'entrée unique du pipeline (Windows, macOS, Linux).

    python pipeline.py all                       # chaîne complète, tests bloquants inclus
    python pipeline.py ingest | prep | dedup | quality | core | test
    python pipeline.py reload --month 2024_03    # rejoue un mois de règlements puis toute la chaîne

Chaque étape est tracée dans meta.pipeline_runs. En cas d'échec : statut FAILED,
message dans logs/alerts.log, code de sortie 1 (les étapes suivantes ne tournent pas).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import duckdb

from ingestion import load_raw
from quality import run_rules

ROOT = Path(__file__).resolve().parent
DB = str(ROOT / "boreal.duckdb")
SOURCES = ROOT / "data" / "sources"
LOGS = ROOT / "logs"
DEDUP_SCRIPT = ROOT / "quality" / "dedup_clients.py"

RUN_ID = datetime.now().strftime("%Y%m%d%H%M%S%f")


class StepFailed(Exception):
    pass


def run_sql_dir(folder: str) -> None:
    con = duckdb.connect(DB)
    for f in sorted((ROOT / "sql" / folder).glob("*.sql")):
        print(f"  [SQL] {folder}/{f.name}")
        con.execute(f.read_text(encoding="utf-8"))
    con.close()


def step_ingest() -> None:
    if load_raw.run(DB, SOURCES) != 0:
        raise StepFailed("ingestion : au moins un fichier en échec (voir meta.ingestion_log)")


def step_prep() -> None:
    run_sql_dir("prep")


def step_dedup() -> None:
    """Produit prep.client_mapping (client_id -> client_id_maitre).
    Script de B s'il existe, sinon mapping identité (aucune fusion)."""
    if DEDUP_SCRIPT.exists():
        print(f"  script {DEDUP_SCRIPT.relative_to(ROOT)}")
        r = subprocess.run([sys.executable, str(DEDUP_SCRIPT), "--db", DB], cwd=ROOT)
        if r.returncode != 0:
            raise StepFailed("déduplication : le script a échoué")
    else:
        print("  quality/dedup_clients.py absent -> mapping identité")
        con = duckdb.connect(DB)
        con.execute("""CREATE OR REPLACE TABLE prep.client_mapping AS
            SELECT DISTINCT client_id, client_id AS client_id_maitre
            FROM prep.clients WHERE client_id IS NOT NULL""")
        con.close()


def step_quality() -> None:
    run_rules.run(DB)


def step_core() -> None:
    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS core")
    # le cœur v0 était fait de vues : on les retire pour laisser place aux tables
    for (name,) in con.execute("""SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'core' AND table_type = 'VIEW'""").fetchall():
        con.execute(f"DROP VIEW core.{name}")
    con.close()
    run_sql_dir("core")


def step_test() -> None:
    env = {**os.environ, "BOREAL_DB": DB}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT, env=env)
    if r.returncode != 0:
        raise StepFailed("tests bloquants en échec : chargement interrompu")


STEPS = {
    "ingest": step_ingest,
    "prep": step_prep,
    "dedup": step_dedup,
    "quality": step_quality,
    "core": step_core,
    "test": step_test,
}
ALL = ["ingest", "prep", "dedup", "quality", "core", "test"]


def log_step(step: str, statut: str, duree: float, message: str | None = None) -> None:
    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")
    con.execute("""CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
        run_id VARCHAR, etape VARCHAR, statut VARCHAR, duree_s DOUBLE, message VARCHAR, horodatage TIMESTAMP)""")
    con.execute("INSERT INTO meta.pipeline_runs VALUES (?,?,?,?,?,?)",
                [RUN_ID, step, statut, duree, message, datetime.now()])
    con.close()


def alert(message: str) -> None:
    LOGS.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} run={RUN_ID} ÉCHEC {message}\n"
    with open(LOGS / "alerts.log", "a", encoding="utf-8") as f:
        f.write(line)
    print("!! " + line.strip(), file=sys.stderr)


def run_steps(names: list[str]) -> int:
    for name in names:
        print(f"== {name}")
        t0 = time.perf_counter()
        try:
            STEPS[name]()
        except Exception as e:  # noqa: BLE001
            msg = f"{name} : {e}"
            log_step(name, "FAILED", time.perf_counter() - t0, str(e)[:1000])
            alert(msg)
            if not isinstance(e, StepFailed):
                traceback.print_exc()
            return 1
        log_step(name, "OK", time.perf_counter() - t0)
    print("Pipeline OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["all", "reload", *STEPS])
    ap.add_argument("--month", help="AAAA_MM pour reload")
    a = ap.parse_args()
    if a.step == "all":
        sys.exit(run_steps(ALL))
    if a.step == "reload":
        if not a.month:
            sys.exit("Usage : python pipeline.py reload --month AAAA_MM")
        rc = load_raw.run(DB, SOURCES, only=f"reglements/reglements_{a.month}.csv", force=True)
        if rc != 0:
            alert(f"reload {a.month} : fichier en échec")
            sys.exit(1)
        sys.exit(run_steps(ALL[1:]))
    sys.exit(run_steps([a.step]))
