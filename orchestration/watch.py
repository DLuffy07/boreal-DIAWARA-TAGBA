"""Déclenchement du pipeline à l'arrivée d'un nouveau fichier de règlements.

Deux modes :
  python orchestration/watch.py                 # surveillance continue (vérifie toutes les 30 s)
  python orchestration/watch.py --once          # une vérification puis sortie (pour le planificateur)

Principe : on compare l'empreinte (hash) de chaque fichier du dossier surveillé à ce que
meta.ingestion_log a déjà chargé. Nouveau fichier ou fichier modifié -> python pipeline.py all.
Le pipeline étant idempotent, un faux déclenchement ne change rien aux données.
Planification mensuelle : voir docs/orchestration.md (Planificateur de tâches Windows / cron).
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "boreal.duckdb"
WATCHED = ROOT / "data" / "sources"
PATTERNS = ["reglements/reglements_*.csv", "crm/*.csv", "contrats/*.csv", "sinistres/*.jsonl", "antifraude/*.csv"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def known_hashes() -> dict[str, str]:
    if not DB.exists():
        return {}
    try:
        con = duckdb.connect(str(DB), read_only=True)
        rows = con.execute("""SELECT fichier, arg_max(hash, horodatage) FROM meta.ingestion_log
                              WHERE statut = 'OK' GROUP BY 1""").fetchall()
        con.close()
        return dict(rows)
    except duckdb.Error:
        return {}


def pending_files() -> list[str]:
    known = known_hashes()
    out = []
    for pat in PATTERNS:
        for p in sorted(WATCHED.glob(pat)):
            rel = p.relative_to(WATCHED).as_posix()
            if known.get(rel) != sha256(p):
                out.append(rel)
    return out


def file_is_stable(rel: str, wait: float = 2.0) -> bool:
    """Évite de lancer le pipeline sur un fichier encore en cours de copie."""
    p = WATCHED / rel
    s1 = p.stat().st_size
    time.sleep(wait)
    return p.stat().st_size == s1


def check_once() -> int:
    new = pending_files()
    if not new:
        print(f"{datetime.now():%H:%M:%S} rien de nouveau")
        return 0
    new = [f for f in new if file_is_stable(f)]
    if not new:
        return 0
    print(f"{datetime.now():%H:%M:%S} nouveaux fichiers : {', '.join(new)} -> lancement du pipeline")
    return subprocess.run([sys.executable, str(ROOT / "pipeline.py"), "all"], cwd=ROOT).returncode


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="une seule vérification (planificateur)")
    ap.add_argument("--interval", type=int, default=30, help="secondes entre deux vérifications")
    a = ap.parse_args()
    if a.once:
        sys.exit(check_once())
    print(f"Surveillance de {WATCHED} toutes les {a.interval} s (Ctrl+C pour arrêter)")
    while True:
        try:
            check_once()
            time.sleep(a.interval)
        except KeyboardInterrupt:
            break
