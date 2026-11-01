"""Modèles des partenaires (annexe E.1)."""
from django.db import models


class Categorie(models.Model):
    """Catégorie d'activité (auto, assurance...), éventuellement hiérarchique."""

    nom = models.CharField(max_length=120)
    type = models.CharField(max_length=60, blank=True)
    categorie_parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sous_categories",
    )

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["nom"]

    def __str__(self):
        return self.nom



class PartenaireQuerySet(models.QuerySet):
    """Requêtes sur les fiches partenaires."""

    def visible_to(self, utilisateur):
        """Fiches visibles d'après la matrice (ressource « Fiches partenaires »).

        Une fiche n'a ni propriétaire ni équipe : seule la portée « toute »
        donne la liste. Les portées restreintes sont à préciser avec SYNESS.
        """
        from applications.comptes.permissions import portees_consultation

        if "toute" in portees_consultation(utilisateur, "Fiches partenaires"):
            return self.filter(fusionnee_dans__isnull=True)
        return self.none()

    def rechercher(self, terme):
        """Recherche par nom, raison sociale, catégorie ou ville."""
        terme = (terme or "").strip()
        if not terme:
            return self
        return self.filter(
            models.Q(nom_commercial__icontains=terme)
            | models.Q(raison_sociale__icontains=terme)
            | models.Q(categorie__nom__icontains=terme)
            | models.Q(localisations__ville__icontains=terme)
        ).distinct()


class Partenaire(models.Model):
    """Fiche d'un partenaire potentiel ou actif."""

    class StatutVerification(models.TextChoices):
        A_VERIFIER = "a_verifier", "À vérifier"
        VERIFIE = "verifie", "Vérifié"
        REJETE = "rejete", "Rejeté"

    class StatutCommercial(models.TextChoices):
        NON_CONTACTE = "non_contacte", "Non contacté"
        A_QUALIFIER = "a_qualifier", "À qualifier"
        QUALIFIE = "qualifie", "Qualifié"
        POTENTIEL = "potentiel", "Partenaire potentiel"
        ACTIF = "actif", "Partenaire actif"

    nom_commercial = models.CharField(max_length=200)
    raison_sociale = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    categorie = models.ForeignKey(
        Categorie,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="partenaires",
    )
    statut_verification = models.CharField(
        max_length=12,
        choices=StatutVerification.choices,
        default=StatutVerification.A_VERIFIER,
    )
    date_derniere_verification = models.DateField(null=True, blank=True)

    fusionnee_dans = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="fiches_fusionnees",
    )


    statut_commercial = models.CharField(
        max_length=14,
        choices=StatutCommercial.choices,
        default=StatutCommercial.NON_CONTACTE,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    objects = PartenaireQuerySet.as_manager()
    class Meta:
        verbose_name = "partenaire"
        verbose_name_plural = "partenaires"
        ordering = ["nom_commercial"]

    def __str__(self):
        return self.nom_commercial


class Localisation(models.Model):
    """Emplacement d'un partenaire : un partenaire peut en avoir plusieurs."""

    partenaire = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="localisations"
    )
    pays = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    ville = models.CharField(max_length=80, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = "localisation"
        verbose_name_plural = "localisations"

    def __str__(self):
        return ", ".join(p for p in (self.adresse, self.ville, self.pays) if p)


class Contact(models.Model):
    """Moyen de contact professionnel : téléphone, e-mail ou site web."""

    class Type(models.TextChoices):
        TELEPHONE = "tel", "Téléphone"
        EMAIL = "email", "E-mail"
        WEB = "web", "Site web"

    partenaire = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="contacts"
    )
    type = models.CharField(max_length=5, choices=Type.choices)
    valeur = models.CharField(max_length=255)

    class Meta:
        verbose_name = "contact"
        verbose_name_plural = "contacts"

    def __str__(self):
        return f"{self.get_type_display()} : {self.valeur}"


class ServicePropose(models.Model):
    """Service ou offre publié par un partenaire, avec son tarif si connu."""

    partenaire = models.ForeignKey(
        Partenaire, on_delete=models.CASCADE, related_name="services"
    )
    libelle = models.CharField(max_length=200)
    tarif = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    devise = models.CharField(max_length=3, blank=True)
    unite = models.CharField(max_length=40, blank=True)
    date_validite = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "service proposé"
        verbose_name_plural = "services proposés"

    def __str__(self):
        return self.libelle
