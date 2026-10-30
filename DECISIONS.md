# Journal des décisions

Ce fichier garde la trace des décisions du projet : quoi, quand, qui, et avec quelles conséquences. Les décisions marquées « à valider » restent des propositions tant que SYNESS ne les a pas confirmées par écrit.

| N° | Date | Décision | Décideur | Statut | Conséquence |
|----|------|----------|----------|--------|-------------|
| 1 | 2026-10-30 | Technologies : Python, Django, PostgreSQL, Redis, Docker | Daouda KA (proposition) | À valider par M. Sy | Pile du plan, section 3 |
| 2 | 2026-10-30 | Noms en français pour le code du projet : dossier `configuration/` au lieu de `config/`, dossier `applications/` au lieu de `apps/` | Daouda KA | À valider par M. Sy | Écart avec la structure du plan (section 2.4), pour faciliter la lecture par SYNESS |
| 3 | 2026-10-30 | Les noms imposés par Django restent en anglais (`views.py`, `urls.py`, `models.py`, `apps.py`) | Daouda KA | Décidé | Django cherche ces noms exacts ; les renommer casserait le projet |
| 4 | 2026-10-30 | Un fichier à la fois, un commit par étape | Daouda KA | Décidé | Historique Git lisible, en ligne avec la boucle de travail du plan (section 8.1) |
| 5 | 2026-10-30 | PostgreSQL installé directement sur le poste de développement ; Docker prévu pour la livraison | Daouda KA | Décidé | Docker sera validé avant le jalon 9 |
| 6 | 2026-10-30 | Première adresse du projet : `/sante/`, qui répond `{"statut": "ok"}` | Daouda KA | Décidé | Permet à Docker et à la supervision de vérifier que l'application tourne |

## Décisions en attente de SYNESS

- Hébergement (VPS ou hébergement existant de SYNESS)
- Première source de collecte
- Mode d'accès à Garage.sn
- Cadre de collaboration (statut, durée, rémunération, propriété du code)