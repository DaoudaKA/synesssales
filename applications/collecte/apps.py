"""Configuration de l'application collecte."""
from django.apps import AppConfig


class CollecteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "applications.collecte"
    verbose_name = "Collecte et qualité"
