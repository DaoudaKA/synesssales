"""Réglages communs à tous les environnements."""
import os
from pathlib import Path

import environ

# Racine du projet : le dossier qui contient manage.py et .env
RACINE_PROJET = Path(__file__).resolve().parent.parent.parent

# Lecture du fichier .env
env = environ.Env()
environ.Env.read_env(RACINE_PROJET / ".env")

# Sécurité : tout vient du .env, rien n'est écrit ici
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Applications de Django (les tiennes viendront plus tard)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Applications du projet
    "applications.noyau",
    "applications.comptes",
    "applications.equipes",
    "applications.partenaires",
    "applications.collecte",
    "applications.ventes",
    "applications.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "configuration.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [RACINE_PROJET / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "applications.notifications.contexte.non_lues",
            ],
        },
    },
]

WSGI_APPLICATION = "configuration.wsgi.application"

# Base de données : lue dans DATABASE_URL (fichier .env)
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Utilisateur personnalisé : connexion par e-mail
AUTH_USER_MODEL = "comptes.Utilisateur"

# Connexion
LOGIN_URL = "connexion"
LOGIN_REDIRECT_URL = "accueil"
LOGOUT_REDIRECT_URL = "connexion"
# Langue et fuseau horaire
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

# Fichiers statiques
STATIC_URL = "static/"
STATIC_ROOT = RACINE_PROJET / "staticfiles"
# Fichiers envoyés (enregistrements) : hors du dépôt Git
MEDIA_URL = "media/"
MEDIA_ROOT = RACINE_PROJET / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Nombre de jours de retard au-delà desquels une relance non faite est signalée
# au chef d'équipe du commercial (escalade).
SEUIL_ESCALADE_RELANCES_JOURS = 2

# Une tâche (hors rendez-vous) dont l'échéance tombe dans ce délai déclenche un rappel.
DELAI_RAPPEL_ECHEANCE_HEURES = 24
# Un rendez-vous qui commence dans ce délai est signalé comme imminent.
DELAI_RDV_IMMINENT_HEURES = 2

# Un prospect en cours sans activité depuis ce nombre de jours est signalé au chef d'équipe.
SEUIL_SANS_SUIVI_JOURS = 7



# --- E-mail (canal de notification) ---
# Sans serveur configuré (variable EMAIL_HOST), les e-mails s'affichent dans la console :
# aucun envoi accidentel en développement ou en test.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "SYNESS Sales <no-reply@synesssales.local>"
)
# Adresse publique de l'application, pour les liens placés dans les e-mails.
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")
# Tentatives d'envoi maximum par notification, et nombre maximum d'e-mails par exécution.
COURRIEL_MAX_TENTATIVES = 3
COURRIEL_PLAFOND_PAR_EXECUTION = 100

# Un objectif est « en écart » quand son avancement est inférieur de ce nombre de points
# (ou plus) à la part de la période déjà écoulée.
TOLERANCE_ECART_OBJECTIF_POINTS = 20
