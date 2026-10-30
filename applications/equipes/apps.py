"""Configuration de l'application equipes."""
from django.apps import AppConfig


class EquipesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "applications.equipes"
    verbose_name = "Équipes"
