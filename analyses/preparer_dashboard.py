"""Recalcule les analyses B, les marts dashboard et la documentation en une commande."""
import argparse
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def run(args):
    subprocess.run([sys.executable,*args],cwd=ROOT,check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',default='boreal.duckdb')
    p.add_argument('--iterations',type=int,default=2000)
    a=p.parse_args()
    database=Path(a.database).resolve()
    if not database.is_file():p.error('Base absente : exécuter d’abord python pipeline.py all.')
    # Le pipeline de A reste le propriétaire des couches raw/prep/core.
    for filename in ['02_mart_segments.py','03_export_indicateurs.py','04_statistiques.py','05_clients_sinistres.py','06_dashboard_marts.py']:
        cmd=['analyses/'+filename,'--database',str(database)]
        if filename=='04_statistiques.py':cmd+=['--iterations',str(a.iterations)]
        print('\n== Analyse B : '+filename,flush=True);run(cmd)
    run(['docs/completer_catalogue_b.py','--database',str(database)])
    # Générateur A paramétré sans modifier pipeline.py.
    sys.path.insert(0,str(ROOT))
    from docs import gen_catalogue
    gen_catalogue.run(str(database))
    print('\nDashboard prêt : python -m streamlit run dashboard/app.py')
