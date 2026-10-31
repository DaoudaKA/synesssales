"""Modèles du pilotage commercial : produits, campagnes et scripts (annexe E.2)."""
from django.db import models
from django.db.models import F, Q


class Produit(models.Model):
    """Un produit ou service commercialisé (par exemple Garage.sn)."""

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"
        ARCHIVE = "archive", "Archivé"

    nom = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    argumentaire = models.TextField(blank=True)
    argumentaire_valide = models.BooleanField(default=False)
    equipe_responsable = models.ForeignKey(
        "equipes.Equipe",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="produits",
    )
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF)

    class Meta:
        verbose_name = "produit"
        verbose_name_plural = "produits"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Campagne(models.Model):
    """Une campagne de prospection pour un produit, sur une zone et une période."""

    nom = models.CharField(max_length=150)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name="campagnes")
    zone = models.CharField(max_length=120, blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    objectif = models.TextField(blank=True)

    class Meta:
        verbose_name = "campagne"
        verbose_name_plural = "campagnes"
        ordering = ["-date_debut"]
        constraints = [
            models.CheckConstraint(
                condition=Q(date_fin__isnull=True) | Q(date_fin__gte=F("date_debut")),
                name="campagne_dates_coherentes",
            ),
        ]

    def __str__(self):
        return self.nom


class Script(models.Model):
    """Script de prospection d'un produit, versionné et soumis à validation."""

    class StatutValidation(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        VALIDE = "valide", "Validé"
        ARCHIVE = "archive", "Archivé"

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="scripts")
    version = models.PositiveIntegerField(default=1)
    contenu = models.TextField()
    statut_validation = models.CharField(
        max_length=10,
        choices=StatutValidation.choices,
        default=StatutValidation.BROUILLON,
    )

    class Meta:
        verbose_name = "script"
        verbose_name_plural = "scripts"
        ordering = ["produit", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["produit", "version"], name="script_version_unique"),
        ]

    def __str__(self):
        return f"{self.produit} — version {self.version}"
