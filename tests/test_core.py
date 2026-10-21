"""Tests bloquants exécutés à chaque lancement du pipeline (étape test).
Un échec interrompt la chaîne : les marts ne sont pas reconstruits."""
import pytest

from conftest import scalar

EPS = 1e-6


# ---------------------------------------------------------------- 1. unicité des clés
@pytest.mark.parametrize("table, key", [
    ("core.dim_client", "client_sk"),
    ("core.dim_contrat", "contrat_id"),
    ("core.dim_segment", "segment_id"),
    ("core.dim_date", "date"),
    ("core.fait_sinistre", "sinistre_id"),
    ("core.fait_reglement", "paiement_id"),
    ("core.fait_exposition", "contrat_id, annee"),
    ("core.v_client_analyse", "client_id_maitre"),
    ("prep.client_mapping", "client_id"),
])
def test_unicite_cles(con, table, key):
    dup = scalar(con, f"SELECT count(*) FROM (SELECT {key} FROM {table} GROUP BY ALL HAVING count(*) > 1)")
    nulls = scalar(con, f"SELECT count(*) FROM {table} WHERE ({key}) IS NULL")
    assert dup == 0 and nulls == 0, f"{table}({key}) : {dup} doublons, {nulls} nulls"


def test_scd2_une_version_courante(con):
    assert scalar(con, """SELECT count(*) FROM (SELECT client_id_maitre FROM core.dim_client
                          WHERE is_current GROUP BY 1 HAVING count(*) <> 1)""") == 0


# ---------------------------------------------------------------- 2. intégrité référentielle
@pytest.mark.parametrize("child, fk, parent, pk", [
    ("core.dim_contrat", "client_id_maitre", "core.dim_client", "client_id_maitre"),
    ("core.dim_contrat", "segment_id", "core.dim_segment", "segment_id"),
    ("core.fait_exposition", "contrat_id", "core.dim_contrat", "contrat_id"),
    ("core.fait_sinistre", "contrat_id", "core.dim_contrat", "contrat_id"),
    ("core.fait_sinistre", "garantie", "core.dim_garantie", "garantie"),
    ("core.fait_reglement", "sinistre_id", "core.fait_sinistre", "sinistre_id"),
    ("prep.client_mapping", "client_id_maitre", "core.dim_client", "client_id_maitre"),
])
def test_integrite_referentielle(con, child, fk, parent, pk):
    orphans = scalar(con, f"SELECT count(*) FROM {child} WHERE {fk} NOT IN (SELECT {pk} FROM {parent})")
    assert orphans == 0, f"{child}.{fk} : {orphans} orphelins"


def test_mapping_couvre_tous_les_clients(con):
    assert scalar(con, """SELECT count(*) FROM prep.clients WHERE client_id IS NOT NULL
                          AND client_id NOT IN (SELECT client_id FROM prep.client_mapping)""") == 0


# ---------------------------------------------------------------- 3. réconciliation brut / cœur / quarantaine
@pytest.mark.parametrize("raw, prep", [
    ("raw.clients", "prep.clients"), ("raw.contrats", "prep.contrats"),
    ("raw.sinistres", "prep.sinistres"), ("raw.reglements", "prep.reglements"),
    ("raw.audits", "prep.audits"),
])
def test_raw_egal_prep(con, raw, prep):
    assert scalar(con, f"SELECT count(*) FROM {raw}") == scalar(con, f"SELECT count(*) FROM {prep}")


@pytest.mark.parametrize("prep, core, key", [
    ("prep.contrats", "core.dim_contrat", "contrat_id"),
    ("prep.sinistres", "core.fait_sinistre", "sinistre_id"),
    ("prep.reglements", "core.fait_reglement", "paiement_id"),
])
def test_chaque_ligne_en_coeur_ou_en_quarantaine(con, prep, core, key):
    total = scalar(con, f"SELECT count(*) FROM {prep}")
    excl = scalar(con, f"SELECT count(*) FROM {prep} WHERE _row_key IN (SELECT _row_key FROM quarantine.lignes_exclues)")
    coeur = scalar(con, f"SELECT count(*) FROM {core}")
    assert total == excl + coeur, f"{prep} : {total} lignes ≠ {coeur} en cœur + {excl} en quarantaine"


def test_reconciliation_montants_reglements(con):
    brut = scalar(con, "SELECT sum(TRY_CAST(montant AS DOUBLE)) FROM raw.reglements")
    coeur = scalar(con, "SELECT sum(montant) FROM core.fait_reglement")
    quar = scalar(con, """SELECT coalesce(sum(montant), 0) FROM prep.reglements
                          WHERE _row_key IN (SELECT _row_key FROM quarantine.lignes_exclues)""")
    assert abs(brut - (coeur + quar)) < 0.01, f"brut {brut:.2f} ≠ cœur {coeur:.2f} + quarantaine {quar:.2f}"


def test_montant_paye_egal_reglements(con):
    a = scalar(con, "SELECT sum(montant_paye) FROM core.fait_sinistre")
    b = scalar(con, "SELECT sum(montant) FROM core.fait_reglement")
    assert abs(a - b) < 0.01


# ---------------------------------------------------------------- 4. exposition
def test_exposition_positive_et_bornee(con):
    # 366 / 365.25 : une année bissextile entièrement couverte (contrat §Exposition)
    bad = scalar(con, f"""SELECT count(*) FROM core.fait_exposition
                          WHERE exposition_annees <= 0 OR exposition_annees > 366 / 365.25 + {EPS}""")
    assert bad == 0


def test_exposition_totale_egale_duree_des_contrats(con):
    attendu = scalar(con, """SELECT sum(date_diff('day', date_effet,
                               least(coalesce(date_resiliation, DATE '2025-07-01'), DATE '2025-07-01')) / 365.25)
                             FROM core.dim_contrat""")
    obtenu = scalar(con, "SELECT sum(exposition_annees) FROM core.fait_exposition")
    assert abs(attendu - obtenu) < 1e-3


def test_prime_acquise_coherente(con):
    bad = scalar(con, """SELECT count(*) FROM core.fait_exposition e JOIN core.dim_contrat c USING (contrat_id)
                         WHERE abs(e.prime_acquise - c.prime_annuelle * e.exposition_annees) > 0.01""")
    assert bad == 0


# ---------------------------------------------------------------- 5. cohérence métier
def test_charge_positive(con):
    assert scalar(con, "SELECT count(*) FROM core.fait_sinistre WHERE charge < 0 OR reserve_restante < 0") == 0


def test_jointure_client_ne_duplique_rien(con):
    a = scalar(con, "SELECT count(*) FROM core.dim_contrat")
    b = scalar(con, "SELECT count(*) FROM core.dim_contrat JOIN core.v_client_analyse USING (client_id_maitre)")
    assert a == b


def test_quarantaine_a_toujours_un_motif(con):
    assert scalar(con, "SELECT count(*) FROM quarantine.anomalies WHERE motif IS NULL OR rule_id IS NULL") == 0
