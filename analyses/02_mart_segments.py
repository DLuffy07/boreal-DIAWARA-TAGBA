"""Construction transactionnelle du premier mart depuis le cœur de A."""
import argparse
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    'dim_contrat': ['contrat_id','client_id_maitre','produit','zone_risque','formule','canal_distribution','date_resiliation'],
    'dim_segment': ['segment_id','produit','zone_risque','formule','canal_distribution'],
    'v_client_analyse': ['client_id_maitre','tranche_age'],
    'fait_exposition': ['contrat_id','annee','segment_id','exposition_annees','prime_acquise','resilie_dans_annee'],
    'fait_sinistre': ['sinistre_id','contrat_id','date_survenance','statut','montant_paye','reserve_restante','charge']
}


def require(db, query, label):
    if db.execute(query).fetchone()[0]:
        raise ValueError(label)


def validate_core(db):
    for table, columns in REQUIRED.items():
        try:
            db.execute('SELECT '+','.join(columns)+' FROM core.'+table+' LIMIT 0')
        except duckdb.Error as exc:
            raise ValueError(f'Contrat non respecté : core.{table} doit fournir {columns}') from exc
    for table, key in [('dim_contrat','contrat_id'),('dim_segment','segment_id'),('v_client_analyse','client_id_maitre'),('fait_sinistre','sinistre_id')]:
        require(db,f'SELECT count(*)-count(DISTINCT {key}) FROM core.{table}',f'Clé absente ou dupliquée : {table}.{key}')
    require(db,'''SELECT count(*) FROM (SELECT contrat_id,annee FROM core.fait_exposition GROUP BY ALL HAVING count(*)>1)''','Expositions dupliquées par contrat/année')
    require(db,'''SELECT count(*) FROM (SELECT produit,zone_risque,formule,canal_distribution FROM core.dim_segment GROUP BY ALL HAVING count(*)>1)''','Segments métier dupliqués')
    require(db,'''SELECT count(*) FROM core.dim_contrat c LEFT JOIN core.v_client_analyse cl USING(client_id_maitre) WHERE cl.client_id_maitre IS NULL''','Contrat sans profil client unique')
    require(db,'''SELECT count(*) FROM core.dim_contrat c LEFT JOIN core.dim_segment s ON c.produit=s.produit AND c.zone_risque=s.zone_risque AND c.formule=s.formule AND c.canal_distribution=s.canal_distribution WHERE s.segment_id IS NULL''','Contrat sans segment métier correspondant')
    for table in ['fait_exposition','fait_sinistre']:
        require(db,f'SELECT count(*) FROM core.{table} f LEFT JOIN core.dim_contrat c USING(contrat_id) WHERE c.contrat_id IS NULL',f'{table} sans contrat')
    require(db,'''SELECT count(*) FROM core.fait_exposition WHERE annee IS NULL OR annee NOT BETWEEN 2020 AND 2025 OR exposition_annees IS NULL OR exposition_annees<=0 OR prime_acquise IS NULL OR prime_acquise<=0 OR resilie_dans_annee IS NULL''','Exposition/primes/année/résiliation invalides')
    require(db,'''SELECT count(*) FROM core.fait_exposition e JOIN core.dim_contrat c USING(contrat_id) JOIN core.dim_segment s ON c.produit=s.produit AND c.zone_risque=s.zone_risque AND c.formule=s.formule AND c.canal_distribution=s.canal_distribution WHERE e.segment_id IS DISTINCT FROM s.segment_id''','Segment du fait exposition incohérent avec le contrat')
    require(db,'''SELECT count(*) FROM core.fait_sinistre WHERE date_survenance IS NULL OR date_survenance<DATE '2020-01-01' OR date_survenance>DATE '2025-06-30' OR statut IS NULL OR statut NOT IN ('OUVERT','CLOTURE','SANS_SUITE','REJETE') OR montant_paye IS NULL OR reserve_restante IS NULL OR charge IS NULL''','Sinistre incomplet, statut inconnu ou hors observation')
    require(db,'''SELECT count(*) FROM core.fait_sinistre WHERE abs(charge-montant_paye-reserve_restante)>0.01''','Charge différente du payé + réserve')


def build(database, output):
    database=Path(database)
    if not database.is_file():
        raise FileNotFoundError(f'Base absente : {database}. Récupérer boreal.duckdb auprès de A ; ne pas utiliser la base de mapping.')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(database)) as db:
        db.execute('BEGIN TRANSACTION')
        try:
            validate_core(db)
            db.execute('CREATE SCHEMA IF NOT EXISTS marts')
            db.execute((ROOT/'sql/marts/01_mart_segments.sql').read_text(encoding='utf-8'))
            # Réconciliation indépendante après construction : blocage avant COMMIT.
            for column,source in [
                ('exposition_annees','SELECT sum(exposition_annees) FROM core.fait_exposition'),
                ('primes_acquises','SELECT sum(prime_acquise) FROM core.fait_exposition'),
                ('charge_retenue',"SELECT sum(charge) FROM core.fait_sinistre WHERE statut NOT IN ('SANS_SUITE','REJETE')"),
                ('nb_sinistres_retenus',"SELECT count(*) FROM core.fait_sinistre WHERE statut NOT IN ('SANS_SUITE','REJETE')"),
                ('nb_contrats_exposes','SELECT count(*) FROM core.fait_exposition'),
                ('nb_resiliations',"SELECT count(*) FROM core.dim_contrat WHERE date_resiliation BETWEEN DATE '2020-01-01' AND DATE '2025-06-30'"),
                ('montant_paye_tous_statuts','SELECT sum(montant_paye) FROM core.fait_sinistre')]:
                actual=db.execute(f'SELECT coalesce(sum({column}),0) FROM marts.mart_segments').fetchone()[0]
                expected=db.execute(source).fetchone()[0] or 0
                if abs(float(actual)-float(expected))>max(1e-7,abs(float(expected))*1e-10):
                    raise ValueError(f'Réconciliation en échec : {column}')
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK')
            raise
        df=db.execute('SELECT * FROM marts.mart_segments ORDER BY annee,segment_id,tranche_age').df()
        df.to_csv(output/'mart_segments.csv',index=False)
        print(f'Mart créé : {len(df)} lignes. Export : {output / "mart_segments.csv"}')
        print('Les valeurs de taux sont des ratios bruts : 0.70 représente 70 %.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True,type=Path)
    p.add_argument('--output',default=ROOT/'outputs',type=Path)
    a=p.parse_args()
    build(a.database,a.output)
