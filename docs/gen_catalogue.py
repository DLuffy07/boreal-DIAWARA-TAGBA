"""Génère docs/catalogue.md à partir de la base (structure réelle) et de docs/catalogue.yaml (définitions).

    python -m docs.gen_catalogue

Les colonnes présentes en base mais non décrites sont signalées « NON DOCUMENTÉE »
et comptées en fin d'exécution : B ajoute la description de ses marts dans catalogue.yaml.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

HERE = Path(__file__).resolve().parent
SCHEMAS = ["raw", "prep", "quarantine", "core", "marts", "meta"]
TITRES = {"raw": "Couche brute", "prep": "Préparation", "quarantine": "Quarantaine",
          "core": "Cœur (schéma en étoile)", "marts": "Marts", "meta": "Métadonnées d'exploitation"}


def run(db: str = str(HERE.parent / "boreal.duckdb")) -> int:
    cat = yaml.safe_load((HERE / "catalogue.yaml").read_text(encoding="utf-8"))
    communes, tables = cat.get("communes", {}), cat.get("tables", {})
    con = duckdb.connect(db, read_only=True)
    cols = con.execute(f"""
        SELECT c.table_schema, c.table_name, t.table_type, c.column_name, c.data_type
        FROM information_schema.columns c
        JOIN information_schema.tables t USING (table_schema, table_name)
        WHERE c.table_schema IN ({','.join(repr(s) for s in SCHEMAS)})
        ORDER BY c.table_schema, c.table_name, c.ordinal_position""").fetchall()
    counts = {}
    for s, t, typ, *_ in cols:
        if (s, t) not in counts and typ == "BASE TABLE":
            counts[(s, t)] = con.execute(f'SELECT count(*) FROM "{s}"."{t}"').fetchone()[0]
    con.close()

    out = ["# Catalogue des données", "",
           "Généré automatiquement par `docs/gen_catalogue.py` à chaque lancement du pipeline "
           "(structure lue dans la base, définitions dans `docs/catalogue.yaml`).", ""]
    manquantes = []
    current = None
    for s in SCHEMAS:
        ts = [(t, typ) for (ss, t, typ, *_r) in cols if ss == s]
        ts = list(dict.fromkeys(ts))
        if not ts:
            continue
        out += [f"## {TITRES[s]} (`{s}`)", ""]
        for t, typ in ts:
            full = f"{s}.{t}"
            meta = tables.get(full, {})
            nb = counts.get((s, t))
            kind = "vue" if typ == "VIEW" else f"{nb:,} lignes".replace(",", " ")
            out += [f"### `{full}` · {kind}", "", meta.get("description", "**NON DOCUMENTÉE**"), "",
                    "| Colonne | Type | Définition |", "|---|---|---|"]
            if "description" not in meta:
                manquantes.append(full)
            for ss, tt, _typ, col, dtype in cols:
                if (ss, tt) != (s, t):
                    continue
                d = (meta.get("colonnes") or {}).get(col) or communes.get(col)
                if not d:
                    manquantes.append(f"{full}.{col}")
                    d = "**NON DOCUMENTÉE**"
                out.append(f"| `{col}` | {dtype} | {d} |")
            out.append("")
    (HERE / "catalogue.md").write_text("\n".join(out), encoding="utf-8")
    print(f"  docs/catalogue.md écrit ({len(counts)} tables)")
    if manquantes:
        print(f"  {len(manquantes)} élément(s) non documenté(s) : " + ", ".join(manquantes[:15])
              + (" ..." if len(manquantes) > 15 else ""))
    return 0


if __name__ == "__main__":
    run()
