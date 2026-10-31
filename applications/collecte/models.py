"""Modèles de la collecte, de la provenance et de la qualité (annexe E.1)."""
from django.conf import settings
from django.db import models
from django.db.models import F, Q

from applications.partenaires.models import Partenaire


class SourceDonnees(models.Model):
    """Une source de données : site public, fichier, API, saisie..."""

    nom = models.CharField(max_length=150, unique=True)
    type = models.CharField(max_length=60, blank=True)
    url = models.URLField(blank=True)
    conditions_validees = models.BooleanField(
        default=False,
        help_text="Les conditions d'usage de la source ont été vérifiées (chapitre 4.7).",
    )

    class Meta:
        verbose_name = "source de données"
        verbose_name_plural = "sources de données"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Collecte(models.Model):
    """Une exécution de collecte auprès d'une source."""

    class Statut(models.TextChoices):
        EN_COURS = "en_cours", "En cours"
        TERMINEE = "terminee", "Terminée"
        EN_ERREUR = "en_erreur", "En erreur"

    source = models.ForeignKey(
        SourceDonnees, on_delete=models.PROTECT, related_name="collectes"
    )
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.EN_COURS)
    nb_fiches = models.PositiveIntegerField(default=0)
    nb_erreurs = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "collecte"
        verbose_name_plural = "collectes"
        ordering = ["-date_debut"]

    def __str__(self):
        return f"{self.source} — {self.date_debut:%d/%m/%Y}"


class Provenance(models.Model):
    """D'où vient une valeur d'une fiche partenaire, et avec quelle confiance."""

    class Niveau(models.TextChoices):
        INCONNU = "inconnu", "Inconnu"
        COLLECTE = "collecte", "Collecté"
        CONFIRME = "confirme", "Confirmé"

    partenaire = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="provenances"
    )
    source = models.ForeignKey(
        SourceDonnees, on_delete=models.PROTECT, related_name="provenances"
    )
    collecte = models.ForeignKey(
        Collecte,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="provenances",
    )
    champ = models.CharField(max_length=80)
    valeur = models.TextField(blank=True)
    date_collecte = models.DateTimeField()
    niveau = models.CharField(max_length=10, choices=Niveau.choices, default=Niveau.INCONNU)

    class Meta:
        verbose_name = "provenance"
        verbose_name_plural = "provenances"
        ordering = ["-date_collecte"]

    def __str__(self):
        return f"{self.partenaire} : {self.champ} ({self.get_niveau_display()})"


class Verification(models.Model):
    """Contrôle d'une fiche partenaire par un utilisateur."""

    class Resultat(models.TextChoices):
        CONFORME = "conforme", "Conforme"
        A_CORRIGER = "a_corriger", "À corriger"
        REJETE = "rejete", "Rejeté"

    partenaire = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="verifications"
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="verifications",
    )
    date = models.DateTimeField(auto_now_add=True)
    resultat = models.CharField(max_length=12, choices=Resultat.choices)
    commentaire = models.TextField(blank=True)

    class Meta:
        verbose_name = "vérification"
        verbose_name_plural = "vérifications"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.partenaire} : {self.get_resultat_display()}"


class AlerteDoublon(models.Model):
    """Deux fiches suspectées de désigner le même partenaire."""

    class Statut(models.TextChoices):
        OUVERTE = "ouverte", "Ouverte"
        FUSIONNEE = "fusionnee", "Fusionnée"
        REJETEE = "rejetee", "Rejetée"

    partenaire_a = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="alertes_doublon_a"
    )
    partenaire_b = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="alertes_doublon_b"
    )
    score_similarite = models.FloatField()
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.OUVERTE)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "alerte de doublon"
        verbose_name_plural = "alertes de doublon"
        ordering = ["-score_similarite"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(partenaire_a=F("partenaire_b")),
                name="doublon_deux_fiches_distinctes",
            ),
            models.UniqueConstraint(
                fields=["partenaire_a", "partenaire_b"], name="doublon_paire_unique"
            ),
        ]

    def __str__(self):
        return f"{self.partenaire_a} / {self.partenaire_b} ({self.score_similarite:.2f})"
