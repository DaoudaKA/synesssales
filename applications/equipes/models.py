"""Modèles des équipes (annexe E.2)."""
from django.conf import settings
from django.db import models


class Equipe(models.Model):
    """Une équipe commerciale, dirigée par un chef d'équipe."""

    nom = models.CharField(max_length=120, unique=True)
    chef_equipe = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipes_dirigees",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "équipe"
        verbose_name_plural = "équipes"
        ordering = ["nom"]

    def __str__(self):
        return self.nom
