"""Configuration de l'application partenaires."""
from django.apps import AppConfig


class PartenairesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "applications.partenaires"
    verbose_name = "Partenaires"
