"""Modèle des notifications (annexe E.2)."""
from django.conf import settings
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    """Un message adressé à un utilisateur, selon une priorité et un canal."""

    class Priorite(models.TextChoices):
        BASSE = "basse", "Basse"
        MOYENNE = "moyenne", "Moyenne"
        HAUTE = "haute", "Haute"

    class Canal(models.TextChoices):
        APPLICATION = "application", "Application"
        EMAIL = "email", "E-mail"
        SMS = "sms", "SMS ou messagerie"

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=80)
    message = models.TextField(blank=True)
    priorite = models.CharField(max_length=7, choices=Priorite.choices, default=Priorite.MOYENNE)
    canal = models.CharField(max_length=11, choices=Canal.choices, default=Canal.APPLICATION)
    date = models.DateTimeField(auto_now_add=True)
    lue = models.BooleanField(default=False)
    # Adresse interne de la page concernée (par exemple « /prospects/12/ »).
    lien = models.CharField(max_length=200, blank=True)
    # Clé de regroupement : la même alerte pour la même personne n'est créée qu'une fois
    # (par exemple « relance-en-retard:45 »). Vide = pas de regroupement.
    cle = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["destinataire", "cle"],
                condition=~Q(cle=""),
                name="notification_cle_unique_par_destinataire",
            ),
        ]

    def __str__(self):
        return f"{self.type} → {self.destinataire}"
