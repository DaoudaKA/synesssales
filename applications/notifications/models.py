"""Modèle des notifications (annexe E.2)."""
from django.conf import settings
from django.db import models


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

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.type} → {self.destinataire}"
