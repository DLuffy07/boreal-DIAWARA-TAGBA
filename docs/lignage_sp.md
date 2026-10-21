# Lignage d'un indicateur : le ratio sinistres / primes (S/P)

S/P = charge des sinistres retenus / primes acquises (définitions : `docs/contrat.md`).

```mermaid
flowchart LR
  subgraph Sources
    F1[contrats/contrats.csv]
    F2[sinistres/sinistres.jsonl]
    F3[reglements/reglements_AAAA_MM.csv<br/>64 fichiers]
  end
  subgraph Brut
    R1[raw.contrats]
    R2[raw.sinistres]
    R3[raw.reglements]
  end
  subgraph Préparation
    P1[prep.contrats]
    P2[prep.sinistres]
    P3[prep.reglements]
    Q[quality/rules.yaml<br/>Q03 Q04 Q05 Q06 Q16 Q20 Q22...]
    QA[(quarantine.anomalies)]
  end
  subgraph Cœur
    C1[core.dim_contrat]
    C2[core.fait_exposition<br/>prime_acquise]
    C3[core.fait_reglement]
    C4[core.fait_sinistre<br/>charge, retenu]
  end
  subgraph Marts
    M[marts.mart_segments<br/>marts.mart_portefeuille_mensuel]
  end
  D[Dashboard<br/>page Portefeuille : S/P et alerte 70 %]

  F1 --> R1 --> P1
  F2 --> R2 --> P2
  F3 --> R3 --> P3
  P1 & P2 & P3 --> Q --> QA
  P1 -->|lignes valides| C1 --> C2
  P3 -->|lignes valides| C3 --> C4
  P2 -->|lignes valides| C4
  C2 -->|somme prime_acquise| M
  C4 -->|somme charge des retenus| M
  M --> D
```

## Étape par étape

| Étape | Objet | Transformation | Contrôle |
|---|---|---|---|
| 1 | Fichiers sources | Aucune | Empreinte SHA-256 dans `meta.ingestion_log` |
| 2 | `raw.*` | Copie fidèle en texte, colonnes alignées par nom (`montant_eur` -> `montant`) | Lignes lues = lignes chargées + rejetées |
| 3 | `prep.*` | Typage (dates, montants), normalisation des libellés | Lignes raw = lignes prep (test) |
| 4 | Règles qualité | Primes ≤ 0 (Q03), résiliation ≤ effet (Q04), déclaration avant survenance (Q05), hors couverture (Q06), contrat exclu (Q16), paiement en double (Q20), sinistre exclu (Q22) | Chaque ligne est en cœur ou en quarantaine (test) |
| 5 | `core.fait_exposition` | Découpage contrat × année ; exposition = jours couverts / 365,25 ; prime acquise = prime annuelle × exposition | Exposition > 0 et ≤ 366/365,25 ; somme = durée totale des contrats (tests) |
| 6 | `core.fait_sinistre` | Montant payé = somme des règlements valides ; réserve restante pour les sinistres ouverts ; charge = payé + réserve ; retenu = hors sans suite et rejeté | Montants brut = cœur + quarantaine (test) |
| 7 | Marts | Agrégation séparée des primes (par période couverte) et de la charge (par année de survenance), puis jointure au grain cible | Somme des marts = somme du cœur |
| 8 | Dashboard | Lecture seule des marts ; alerte orange au-dessus de 70 %, rouge au-dessus de 100 % | Chiffres identiques au dossier |
