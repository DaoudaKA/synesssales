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




## 2026-10-30

- PostgreSQL 18 installé en direct sur le poste de développement. La CI et le plan utilisent la 16 : à aligner avant la livraison.
- Utilisateur personnalisé (connexion par e-mail) déclaré avant les premières migrations métier, car le changer ensuite est très coûteux.
- `PermissionMetier` : nom choisi pour ne pas confondre avec la `Permission` interne de Django.
- Un compte suspendu ne peut pas se connecter (`is_active` dérivé du statut).
- `SECURE_HSTS_PRELOAD` non activé : décision irréversible, à prendre quand le domaine de production existe.
- Suppression d'un chef d'équipe ou d'une équipe : pas de suppression en cascade (`SET_NULL`), pour ne perdre ni équipe ni utilisateur.


| 7 | 2026-10-30 | PostgreSQL 18 installé sur le poste de développement ; PostgreSQL 16 pour la CI et Docker | Daouda KA | Décidé | À aligner avant la livraison |
| 8 | 2026-10-30 | Utilisateur personnalisé (connexion par e-mail), déclaré avant les premières migrations métier | Daouda KA | Décidé | Changer de modèle utilisateur plus tard serait très coûteux |
| 9 | 2026-10-30 | `PermissionMetier` : nom choisi pour ne pas confondre avec la `Permission` interne de Django | Daouda KA | Décidé | Matrice de l'annexe G à charger dans ce modèle (jalon 1) |
| 10 | 2026-10-30 | Un compte suspendu ne peut pas se connecter (`is_active` dérivé du statut) | Daouda KA | Décidé | |
| 11 | 2026-10-30 | `SECURE_HSTS_PRELOAD` non activé | Daouda KA | Décidé | Irréversible : à décider quand le domaine de production existe |
| 12 | 2026-10-31 | Suppression d'un chef d'équipe ou d'une équipe : pas de suppression en cascade (`SET_NULL`) | Daouda KA | Décidé | On ne perd ni équipe ni utilisateur |
| 13 | 2026-10-31 | `PROTECT` sur les sources, produits, prospects et contrats | Daouda KA | Décidé | Une donnée référencée ne peut pas être supprimée par erreur : traçabilité |
| 14 | 2026-10-31 | Une affectation terminée garde sa date de fin au lieu d'être supprimée | Daouda KA | Décidé | Conserve l'historique (cahier des charges, 6.4) |
| 15 | 2026-10-31 | Un enregistrement vocal sans consentement est refusé par la base de données | Daouda KA | À valider par M. Sy | Dépend de la téléphonie et de la conformité (cahier des charges, chapitre 8) |
| 16 | 2026-10-31 | Journal d'audit : modification et suppression d'une entrée interdites dans le modèle | Daouda KA | Décidé | Protection de base, à renforcer au jalon 1 (les opérations en masse ne sont pas bloquées) |
| 17 | 2026-10-31 | Type de notification en texte libre | Daouda KA | Décidé | La liste des événements reste à valider avec SYNESS |
| 18 | 2026-10-31 | Python 3.12 dans l'image Docker | Daouda KA | Décidé | Version visée par ruff et par le plan ; Django 5.2 la supporte |

| 19 | 2026-10-31 | Les droits viennent uniquement des rôles : un compte administrateur Django n'a pas de droit métier automatique, un compte suspendu n'en a aucun | Daouda KA | Décidé | La matrice reste la seule source de vérité |
| 20 | 2026-10-31 | Périmètre « * » de la matrice appliqué comme l'équipe de la personne et les équipes qu'elle dirige | Daouda KA | À valider par M. Sy | Hiérarchie du responsable commercial, produit et zone non appliqués : question 5 du cahier des charges |
| 21 | 2026-10-31 | La matrice de l'annexe G est chargée depuis un seul fichier (`matrice.py`) | Daouda KA | À valider par M. Sy | Le tableau est une proposition à relire par SYNESS ; un test vérifie le chargement, pas la justesse du tableau |
| 22 | 2026-10-31 | Journal d'audit branché sur l'administration (suppressions, modifications de droits), en lecture seule | Daouda KA | Décidé | Les exports et validations devront appeler `journaliser` quand leurs écrans existeront |
| 23 | 2026-10-31 | Hachage de mot de passe léger pendant les tests uniquement | Daouda KA | Décidé | Tests passés de 142 s à environ 40 s |
| 24 | 2026-10-31 | Police Lexend chargée depuis Google Fonts en développement | Daouda KA | À revoir avant la livraison | Héberger la police dans le projet : évite la dépendance externe et l'envoi de l'adresse IP des visiteurs à Google |
