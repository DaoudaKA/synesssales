# SYNESS Sales

Plateforme de collecte de données et de pilotage commercial pour l'écosystème SYNESS. Premier produit : Garage.sn.

**État :** jalon 0 (socle du projet) en cours. Aucune fonction métier n'est encore livrée.

## Prérequis

- Python 3.12 ou plus (développé avec Python 3.14)
- PostgreSQL 16 ou plus, installé sur le poste
- Git

## Installation

1. Récupérer le code :

   ```
   git clone https://github.com/DaoudaKA/synesssales.git
   cd synesssales
   ```

2. Créer et activer l'environnement virtuel (Windows PowerShell) :

   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   Sur Mac ou Linux : `source .venv/bin/activate`

3. Installer les bibliothèques :

   ```
   pip install -r requirements-dev.txt
   ```

4. Créer la configuration :

   ```
   Copy-Item .env.example .env
   ```

   Ouvrir `.env` et renseigner `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` et `DATABASE_URL` (même mot de passe). Éviter les caractères spéciaux (`@ : / # ? %`) dans le mot de passe. Le fichier `.env` ne doit jamais être envoyé sur GitHub.

5. Préparer PostgreSQL : créer la base `synesssales` et l'utilisateur `app`, avec le droit de créer des bases pour les tests :

   ```sql
   ALTER USER app CREATEDB;
   ```

6. Appliquer les migrations puis lancer le serveur :

   ```
   python manage.py migrate
   python manage.py runserver
   ```

7. Vérifier : ouvrir http://127.0.0.1:8000/sante/ ; la réponse attendue est `{"statut": "ok"}`.

## Contrôles de qualité

```
pytest
ruff check .
```

Les deux doivent réussir avant chaque commit.

## Structure

| Dossier | Rôle |
|---|---|
| `configuration/` | Réglages Django (`parametres/base.py`, `dev.py`, `prod.py`) |
| `applications/` | Modules du projet (aujourd'hui : `noyau`) |
| `tests/` | Tests automatiques |
| `docs/` | Documentation |

## Docker

Prévu pour la livraison (`docker-compose.yml`), pas encore validé.

## Documents du projet

- `DECISIONS.md` : journal des décisions
- `REGLES_PROJET.md` : règles de travail