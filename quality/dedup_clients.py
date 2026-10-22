"""Mapping clients depuis raw.clients ; appelé par pipeline.py dedup --db."""
import argparse
import json
from pathlib import Path
import duckdb
import pandas as pd

def build_mapping(clients):
    c = clients.copy()
    c['client_id'] = pd.to_numeric(c['client_id'], errors='raise').astype('int64')
    if c['client_id'].duplicated().any():
        raise ValueError('Identifiants clients non uniques : arrêter et examiner les sources.')
    # Seules les chaînes vides sont des valeurs manquantes : ne pas transformer les empreintes.
    c['email_hash'] = c['email_hash'].fillna('').astype(str).str.strip()
    birth = c['date_naissance'].fillna('').astype(str).str.strip()
    c['birth_parsed'] = pd.to_datetime(birth, format='%d/%m/%Y', errors='coerce')
    c['client_id_maitre'] = c['client_id']
    c['motif'] = 'IDENTIFIANT_CONSERVE'
    reviews = []
    for email, group in c[c.email_hash.ne('')].groupby('email_hash', sort=True):
        if len(group) < 2:
            continue
        reasons = []
        if group.birth_parsed.isna().any():
            reasons.append('NAISSANCE_MANQUANTE_OU_INVALIDE')
        elif group.birth_parsed.nunique() != 1:
            reasons.append('CONFLIT_DATE_NAISSANCE')
        # Avec ces sources sans historique, conserver séparément tout groupe contradictoire.
        for col in ['region', 'csp', 'consent_marketing']:
            if group[col].fillna('').nunique() > 1:
                reasons.append('CONFLIT_' + col.upper())
        if reasons:
            for idx in group.index:
                c.loc[idx, 'motif'] = 'REVUE_MANUELLE'
                reviews.append({'client_id': int(c.loc[idx, 'client_id']), 'email_hash': email,
                                'motif': '|'.join(reasons)})
            continue
        master = int(group.client_id.min())
        c.loc[group.index, 'client_id_maitre'] = master
        c.loc[group.index, 'motif'] = 'EMAIL_ET_NAISSANCE_IDENTIQUES'
    mapping = c[['client_id', 'client_id_maitre']].sort_values('client_id').reset_index(drop=True)
    detail = c[['client_id', 'client_id_maitre', 'email_hash', 'date_naissance', 'motif']].sort_values('client_id')
    review = pd.DataFrame(reviews, columns=['client_id', 'email_hash', 'motif'])
    return mapping, detail, review


def run(database):
    database=Path(database)
    if not database.is_file():
        raise FileNotFoundError(database)
    with duckdb.connect(str(database)) as db:
        clients=db.execute("SELECT client_id, date_naissance, region, csp, consent_marketing, email_hash FROM raw.clients").df()
        mapping, detail, review=build_mapping(clients)
        db.execute('BEGIN TRANSACTION')
        try:
            db.execute('CREATE SCHEMA IF NOT EXISTS prep')
            db.execute('CREATE SCHEMA IF NOT EXISTS quarantine')
            db.register('mapping_df',mapping)
            db.register('review_df',review)
            db.execute('CREATE OR REPLACE TABLE prep.client_mapping AS SELECT client_id::INTEGER AS client_id, client_id_maitre::INTEGER AS client_id_maitre FROM mapping_df')
            db.execute('CREATE OR REPLACE TABLE quarantine.clients_a_revoir AS SELECT client_id::INTEGER AS client_id, email_hash::VARCHAR AS email_hash, motif::VARCHAR AS motif FROM review_df')
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK')
            raise
        out=database.parent/'outputs'
        out.mkdir(exist_ok=True)
        mapping.to_csv(out/'client_mapping.csv',index=False)
        review.to_csv(out/'clients_a_revoir.csv',index=False)
        report={'clients_source':len(mapping),'clients_maitres':mapping.client_id_maitre.nunique(),'clients_fusionnes':int((mapping.client_id!=mapping.client_id_maitre).sum()),'clients_a_revoir':len(review)}
        print(json.dumps(report,ensure_ascii=False))
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='boreal.duckdb')
    a=p.parse_args()
    run(a.db)
