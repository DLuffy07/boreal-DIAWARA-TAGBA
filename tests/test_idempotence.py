"""Rejouer un mois de règlements ne crée aucun doublon et ne change aucun total.
Le test travaille sur une COPIE de la base, la base de production n'est pas touchée."""
import shutil
import sys
from pathlib import Path

import duckdb

from conftest import DB, ROOT

sys.path.insert(0, str(ROOT))
from ingestion import load_raw  # noqa: E402

MOIS = "reglements/reglements_2024_03.csv"


def snapshot(con):
    return con.execute("""SELECT
        (SELECT count(*) FROM raw.reglements),
        (SELECT round(sum(TRY_CAST(montant AS DOUBLE)), 2) FROM raw.reglements),
        (SELECT count(*) FROM raw.reglements WHERE _source_file = ?),
        (SELECT count(*) FROM core.fait_reglement),
        (SELECT round(sum(montant), 2) FROM core.fait_reglement)""", [MOIS]).fetchone()


def test_rejouer_un_mois_ne_cree_aucun_doublon(tmp_path):
    copie = str(tmp_path / "copie.duckdb")
    shutil.copy(DB, copie)
    con = duckdb.connect(copie)
    avant = snapshot(con)
    con.close()

    # 1) même fichier livré à nouveau (même hash) : ignoré
    load_raw.run(copie, ROOT / "data" / "sources", only=MOIS)
    # 2) rechargement forcé du mois : lignes du fichier supprimées puis réinsérées
    load_raw.run(copie, ROOT / "data" / "sources", only=MOIS, force=True)
    # 3) on rejoue toute la chaîne aval sur la copie
    import pipeline  # noqa: E402
    pipeline.DB = copie
    for step in ["prep", "dedup", "quality", "core"]:
        pipeline.STEPS[step]()

    con = duckdb.connect(copie)
    apres = snapshot(con)
    dup = con.execute("""SELECT count(*) FROM (SELECT paiement_id FROM core.fait_reglement
                         GROUP BY 1 HAVING count(*) > 1)""").fetchone()[0]
    con.close()
    assert avant == apres, f"avant {avant} / après {apres}"
    assert dup == 0
