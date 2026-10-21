"""Exécute les règles de quality/rules.yaml sur la couche prep.

- quarantine.anomalies : une ligne par (règle, ligne source), avec motif et traitement.
  Recalculée entièrement à chaque lancement : idempotent.
- meta.qualite_resultats : historique du volume de chaque règle à chaque exécution.
- Aucune ligne n'est supprimée : les lignes « exclure » sont simplement écartées du cœur.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import duckdb
import yaml

RULES = Path(__file__).with_name("rules.yaml")


def run(db: str) -> int:
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))["rules"]
    ids = [r["id"] for r in rules]
    if len(ids) != len(set(ids)):
        sys.exit("rules.yaml : identifiants de règle en double")
    con = duckdb.connect(db)
    con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")
    con.execute("""CREATE OR REPLACE TABLE quarantine.anomalies (
        rule_id VARCHAR, table_source VARCHAR, _row_key VARCHAR, motif VARCHAR,
        dimension VARCHAR, gravite VARCHAR, traitement VARCHAR, detecte_le TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS meta.qualite_resultats (
        run_at TIMESTAMP, rule_id VARCHAR, table_source VARCHAR, libelle VARCHAR, dimension VARCHAR,
        gravite VARCHAR, traitement VARCHAR, correction VARCHAR, volume INTEGER, lignes_table INTEGER,
        taux DOUBLE)""")
    now = datetime.now()
    print(f"{'règle':6} {'table':11} {'trait.':9} {'volume':>7}  libellé")
    for r in rules:
        con.execute(f"""INSERT INTO quarantine.anomalies
            SELECT DISTINCT ?, ?, _row_key, ?, ?, ?, ?, ? FROM ({r['sql']})""",
                    [r["id"], r["table"], r["libelle"], r["dimension"], r["gravite"], r["traitement"], now])
        vol = con.execute("SELECT count(*) FROM quarantine.anomalies WHERE rule_id = ?", [r["id"]]).fetchone()[0]
        total = con.execute(f"SELECT count(*) FROM prep.{r['table']}").fetchone()[0]
        con.execute("INSERT INTO meta.qualite_resultats VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    [now, r["id"], r["table"], r["libelle"], r["dimension"], r["gravite"], r["traitement"],
                     r.get("correction"), vol, total, vol / total if total else None])
        print(f"{r['id']:6} {r['table']:11} {r['traitement']:9} {vol:7}  {r['libelle']}")
    # vue pratique : lignes écartées du cœur (une ligne par ligne source, tous motifs concaténés)
    con.execute("""CREATE OR REPLACE VIEW quarantine.lignes_exclues AS
        SELECT table_source, _row_key, string_agg(rule_id || ' ' || motif, ' ; ' ORDER BY rule_id) AS motifs
        FROM quarantine.anomalies WHERE traitement = 'exclure' GROUP BY 1, 2""")
    con.close()
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="boreal.duckdb")
    sys.exit(run(ap.parse_args().db))
