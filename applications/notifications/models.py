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
    # E-mail : demandé par l'événement, puis envoyé par la commande « envoyer_courriels ».
    par_courriel = models.BooleanField(default=False)
    courriel_envoye_le = models.DateTimeField(null=True, blank=True)
    courriel_tentatives = models.PositiveSmallIntegerField(default=0)
    courriel_erreur = models.CharField(max_length=200, blank=True)

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




class Parametre(models.Model):
    """Valeur d'un seuil ou d'un délai réglé depuis l'écran de paramétrage.

    Sans ligne enregistrée, c'est la valeur par défaut du projet (settings) qui s'applique.
    """

    cle = models.CharField(max_length=60, unique=True)
    valeur = models.PositiveIntegerField()
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "paramètre de notification"
        verbose_name_plural = "paramètres de notification"

    def __str__(self):
        return f"{self.cle} = {self.valeur}"
