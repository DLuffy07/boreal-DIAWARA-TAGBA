# Analyse RGPD de l'entrepôt

## 1. Données personnelles présentes

Les sources sont pseudonymisées : aucun nom, adresse, téléphone ni e-mail en clair. Les données
restent **personnelles au sens du RGPD** : un identifiant pseudonyme combiné à d'autres
informations peut permettre de retrouver une personne (considérant 26).

| Donnée | Où | Nature | Risque de réidentification |
|---|---|---|---|
| `client_id`, `client_id_maitre` | toutes couches | Identifiant pseudonyme | Élevé si la table de correspondance du CRM est accessible |
| `email_hash` | raw, prep | Empreinte de l'e-mail | Moyen : une empreinte sans sel peut être retrouvée en hachant une liste d'e-mails connus |
| `date_naissance` | raw, prep, core | Donnée d'identification | Élevé combinée à la région |
| `region`, `csp` | raw, prep, core | Données socio-démographiques | Faible seules, plus élevé en combinaison |
| `consent_marketing` | raw, prep, core | Choix de la personne | Faible ; doit être respecté pour tout usage commercial |
| Sinistres, montants, fraude confirmée | core | Données de la relation contractuelle | Une fraude confirmée est une donnée sensible pour la personne |

Aucune donnée de santé, d'origine, d'opinion (article 9) ni d'infraction pénale au sens strict
n'est présente. Le résultat d'un audit antifraude doit toutefois être traité avec un accès restreint.

## 2. Mesures de minimisation et de pseudonymisation

- **Cœur et marts** : `email_hash` n'est pas repris dans le cœur ; il ne sert qu'à la
  déduplication en couche prep.
- **Âge plutôt que date de naissance** dans les analyses : les marts utilisent `tranche_age`.
  La date de naissance exacte reste dans `core.dim_client` pour recalculer l'âge.
- **Dashboard** : uniquement des agrégats (segment, région, tranche d'âge). La courbe de
  concentration de la valeur client n'affiche pas d'identifiant.
- **Recommandation à Boréal** : saler l'empreinte e-mail (`sha256(sel + email)`) avec un sel
  conservé hors de l'entrepôt, pour empêcher la réidentification par dictionnaire.

## 3. Durées de conservation proposées

| Couche | Contenu | Durée proposée | Justification |
|---|---|---|---|
| Fichiers sources et `raw` | Copies fidèles | 5 ans après la fin du contrat ou la clôture du sinistre | Délais de prescription (2 ans pour les actions nées du contrat d'assurance, art. L114-1 du Code des assurances ; 5 ans en droit commun) et preuve en cas de litige |
| `quarantine` | Lignes écartées | Même durée que la couche brute | Doit permettre de réconcilier avec la source |
| `prep`, `core` | Données nettoyées | 5 ans après la fin de la relation | Pilotage technique et suivi des sinistres |
| `marts`, dashboard | Agrégats | Sans limite si l'agrégat ne permet pas d'identifier une personne | Données anonymes, hors du champ du RGPD |
| `meta`, `logs` | Journaux techniques | 1 an | Exploitation et audit de la chaîne |
| `consent_marketing = 0` | Prospects sans consentement | Pas d'usage commercial | Article 21 (opposition) |

Ces durées sont à valider avec le DPO de Boréal et ses obligations d'assureur (Code des assurances,
lutte antifraude).

## 4. Droit à l'effacement, couche par couche (article 17)

Procédure pour une demande portant sur un client `X` :

1. **Retrouver tous ses identifiants** via `prep.client_mapping` (un client peut avoir
   plusieurs `client_id` source avant déduplication).
2. **Vérifier les exceptions** (article 17.3) : un sinistre ouvert, un litige ou une obligation
   légale de conservation peuvent justifier de conserver certaines données. Elles sont alors
   **limitées** (accès restreint) plutôt qu'effacées.
3. **Effacer dans chaque couche** :

| Couche | Action |
|---|---|
| Fichiers sources | Demander au système source (CRM, gestion) d'effacer : sinon la donnée revient au prochain chargement |
| `raw` | `DELETE` des lignes du client dans les 5 tables brutes (exception à la règle « aucune modification du brut », tracée dans un registre) |
| `prep`, `quarantine` | Reconstruits depuis `raw` par `python pipeline.py all` : effacement automatique |
| `core`, `marts` | Reconstruits par le pipeline : effacement automatique ; les agrégats sont recalculés |
| `meta` | Ne contient aucune donnée client (fichiers, volumes, statuts) |
| Sauvegardes de `boreal.duckdb` | Effacement à l'expiration de la sauvegarde, la date est tracée dans le registre |

4. **Tracer la demande** dans un registre (date, identifiants, couches traitées) sans y recopier
   les données effacées.

Comme toute la chaîne se reconstruit à partir de la couche brute, l'effacement se fait à un seul
endroit (raw + système source) et se propage par une relance du pipeline.

## 5. Autres droits et points de vigilance

- **Droit d'accès** (article 15) : une requête sur `core` par `client_id_maitre` suffit à
  restituer contrats, sinistres et règlements.
- **Profilage** : la notion de « valeur client » (L4) est descriptive ; elle ne doit pas servir à
  une décision automatisée produisant un effet juridique (article 22) sans intervention humaine.
- **Accès** : la base doit être réservée à l'équipe data ; les résultats d'audit antifraude
  doivent avoir un accès encore plus restreint.
