# Règles du projet

## Contexte

Plateforme interne de collecte de données et de pilotage commercial pour SYNESS. Garage.sn existe déjà : on ne le duplique pas, on s'y connecte seulement en lecture, si un accès est autorisé.

## Pile technique

Python, Django, PostgreSQL, Redis, pytest, ruff.

## Règles obligatoires

- Aucun secret dans le code ni dans les tests : tout passe par les variables d'environnement.
- Une fonction = ses tests = un commit.
- Ne jamais inventer une donnée manquante : la valeur reste « inconnue ».
- Toute collecte exige que la source soit autorisée (`Source.est_autorisee` vrai).
- Toute action sensible est journalisée (audit).
- Les droits sont vérifiés côté serveur, y compris dans l'API.
- Aucune commande destructrice sans accord explicite.
- Aucune donnée personnelle réelle dans les jeux de démonstration.

## Commandes

- Lancer le serveur : `python manage.py runserver`
- Appliquer les migrations : `python manage.py migrate`
- Tests : `pytest`
- Style : `ruff check .`

## Avant de terminer une tâche

Tests verts, `ruff` propre, documentation à jour, `DECISIONS.md` complété.