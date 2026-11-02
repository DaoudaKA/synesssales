# Journal des versions

## Jalon 0 : socle du projet (terminé le 2026-10-31)

- Environnement virtuel, dépendances séparées (production et développement), configuration par `.env`.
- Réglages Django séparés : base, développement et production.
- Qualité : ruff, pytest, pre-commit et intégration continue GitHub.
- Modèles de données de l'annexe E : comptes, équipes, partenaires, collecte, ventes, notifications, journal d'audit.
- Administration Django pour les comptes, équipes et partenaires.
- Lancement par `docker compose up` : base PostgreSQL 16, cache Redis et application.
- Adresse de contrôle : `/sante/`.

## Jalon 1 : utilisateurs, rôles et équipes (en cours)

- Matrice des rôles et permissions de l'annexe G chargée en base (8 rôles, 16 ressources), avec un test sur chaque cellule.
- Contrôle des droits centralisé : un utilisateur sans droit est refusé.
- Filtrage des prospects selon le rôle (propres données, équipe, ensemble).
- Connexion par e-mail, page d'accueil, écran des prospects et page « Accès refusé », aux couleurs SYNESS.
- Journal d'audit branché sur l'administration, en lecture seule.
- Commande de données de démonstration.
- Reste : historique des affectations, droits par produit et par zone, exports et validations dans le journal.


## Jalon 1 : utilisateurs, rôles et équipes

- Modèle utilisateur personnalisé (connexion par e-mail, statut).
- Matrice des droits par rôle (annexe G) et contrôle central des droits.
- Filtrage de la visibilité par rôle (prospects, affectations).
- Journal d'audit immuable branché sur l'administration.
- Historique des affectations avec transfert sans perte.
- Écrans : connexion, accueil, prospects, affectations.
- 113 tests, CI verte.


## Jalon 2 — Référentiel des partenaires (terminé)

- Fiches partenaires avec catégories et localisations, vérification avec historique.
- Détection des doublons (seuil 0,85), fusion sans suppression, rejet.
- Import CSV depuis une source validée, avec provenance par valeur et erreurs isolées par ligne.
- Tests : 177 passés.

## Jalon 4 — Pilotage commercial (terminé)

- Fiche prospect : réaffectation avec historique conservé (qui, quand, motif).
- Avertissement de contact multiple (même partenaire ou nom proche), sans fuite d'information.
- Activités, relances, « Mes relances » avec retards signalés.
- Contrats : soumission, validation, refus avec motif obligatoire ; le prospect devient « Gagné ».
- Objectifs individuels et collectifs, avec réalisation et taux d'atteinte.
- Commande `charger_scenario` pour la démonstration.
- Tests : 246 passés. Décisions 38 à 61.
