# Journal des versions

## Jalon 0 : socle du projet (terminé le 2026-10-31)

- Environnement virtuel, dépendances séparées (production et développement), configuration par `.env`.
- Réglages Django séparés : base, développement et production.
- Qualité : ruff, pytest, pre-commit et intégration continue GitHub.
- Modèles de données de l'annexe E : comptes, équipes, partenaires, collecte, ventes, notifications, journal d'audit.
- Administration Django pour les comptes, équipes et partenaires.
- Lancement par `docker compose up` : base PostgreSQL 16, cache Redis et application.
- Adresse de contrôle : `/sante/`.
