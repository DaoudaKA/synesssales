"""Modèles du pilotage commercial : produits, campagnes et scripts (annexe E.2)."""
from django.conf import settings
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


class ProspectQuerySet(models.QuerySet):
    """Requêtes sur les prospects, filtrées selon les droits de la matrice."""

    def visible_to(self, utilisateur):
        # Import local : évite une dépendance circulaire entre les applications.
        from applications.comptes.permissions import portees

        accordees = portees(utilisateur, "Prospects", "L")
        if "toute" in accordees:
            return self
        conditions = Q(pk__in=[])
        if "propre" in accordees:
            conditions |= Q(commercial=utilisateur)
        if "perimetre" in accordees:
            if utilisateur.equipe_id is not None:
                conditions |= Q(equipe_id=utilisateur.equipe_id)
            conditions |= Q(equipe__chef_equipe=utilisateur)
        return self.filter(conditions)


class Prospect(models.Model):
    """Un prospect : une personne ou une entreprise à convaincre pour un produit."""

    class Statut(models.TextChoices):
        NOUVEAU = "nouveau", "Nouveau"
        CONTACTE = "contacte", "Contacté"
        QUALIFIE = "qualifie", "Qualifié"
        PROPOSITION = "proposition", "Proposition faite"
        GAGNE = "gagne", "Gagné"
        PERDU = "perdu", "Perdu"
        REFUSE = "refuse", "Refusé"

    class Interet(models.TextChoices):
        FAIBLE = "faible", "Faible"
        MOYEN = "moyen", "Moyen"
        FORT = "fort", "Fort"

    nom = models.CharField(max_length=200)
    partenaire = models.ForeignKey(
        "partenaires.Partenaire",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects",
    )
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name="prospects")
    campagne = models.ForeignKey(
        Campagne,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects",
    )
    commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects_suivis",
    )
    equipe = models.ForeignKey(
        "equipes.Equipe",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects",
    )
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.NOUVEAU)
    niveau_interet = models.CharField(max_length=6, choices=Interet.choices, blank=True)
    besoin_identifie = models.TextField(blank=True)
    motif_perte = models.TextField(blank=True)
    date_premier_contact = models.DateField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    objects = ProspectQuerySet.as_manager()

    class Meta:
        verbose_name = "prospect"
        verbose_name_plural = "prospects"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.nom} ({self.produit})"


class Affectation(models.Model):
    """Affectation d'un commercial à un produit, avec son historique."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="affectations"
    )
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="affectations")
    campagne = models.ForeignKey(
        Campagne,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="affectations",
    )
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "affectation"
        verbose_name_plural = "affectations"
        ordering = ["-date_debut"]
        constraints = [
            models.CheckConstraint(
                condition=Q(date_fin__isnull=True) | Q(date_fin__gte=F("date_debut")),
                name="affectation_dates_coherentes",
            ),
        ]

    @property
    def en_cours(self):
        return self.date_fin is None

    def __str__(self):
        return f"{self.utilisateur} → {self.produit}"


class Activite(models.Model):
    """Une interaction avec un prospect : appel, visite, message..."""

    class Type(models.TextChoices):
        APPEL = "appel", "Appel"
        VISITE = "visite", "Visite"
        MESSAGE = "message", "Message"
        PRESENTATION = "presentation", "Présentation"
        PROPOSITION = "proposition", "Proposition"

    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="activites")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="activites",
    )
    type = models.CharField(max_length=14, choices=Type.choices)
    date = models.DateTimeField()
    duree_minutes = models.PositiveIntegerField(null=True, blank=True)
    resultat = models.TextField(blank=True)
    objections = models.TextField(blank=True)
    script = models.ForeignKey(
        Script,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activites",
    )

    class Meta:
        verbose_name = "activité"
        verbose_name_plural = "activités"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.prospect}"


class Tache(models.Model):
    """Une action à faire : relance, rendez-vous, envoi d'une proposition."""

    class Type(models.TextChoices):
        RELANCE = "relance", "Relance"
        RENDEZ_VOUS = "rdv", "Rendez-vous"
        PROPOSITION = "proposition", "Envoi d'une proposition"

    class Statut(models.TextChoices):
        A_FAIRE = "a_faire", "À faire"
        FAITE = "faite", "Faite"
        ANNULEE = "annulee", "Annulée"

    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="taches")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="taches",
    )
    type = models.CharField(max_length=14, choices=Type.choices)
    echeance = models.DateTimeField()
    statut = models.CharField(max_length=8, choices=Statut.choices, default=Statut.A_FAIRE)

    class Meta:
        verbose_name = "tâche"
        verbose_name_plural = "tâches"
        ordering = ["echeance"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.prospect}"


class Contrat(models.Model):
    """Un contrat conclu avec un prospect, soumis à validation par un rôle habilité."""

    class StatutValidation(models.TextChoices):
        SOUMIS = "soumis", "Soumis"
        VALIDE = "valide", "Validé"
        REFUSE = "refuse", "Refusé"

    prospect = models.ForeignKey(Prospect, on_delete=models.PROTECT, related_name="contrats")
    date_signature = models.DateField(null=True, blank=True)
    statut_validation = models.CharField(
        max_length=8, choices=StatutValidation.choices, default=StatutValidation.SOUMIS
    )
    motif_refus = models.TextField(blank=True)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contrats_valides",
    )

    class Meta:
        verbose_name = "contrat"
        verbose_name_plural = "contrats"
        ordering = ["-date_signature"]

    def __str__(self):
        return f"Contrat — {self.prospect}"


class EnregistrementVocal(models.Model):
    """Enregistrement d'une activité, conservé seulement avec consentement."""

    activite = models.OneToOneField(
        Activite, on_delete=models.CASCADE, related_name="enregistrement"
    )
    fichier = models.FileField(upload_to="enregistrements/")
    duree_secondes = models.PositiveIntegerField(null=True, blank=True)
    consentement = models.BooleanField(default=False)
    date_expiration = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "enregistrement vocal"
        verbose_name_plural = "enregistrements vocaux"
        constraints = [
            models.CheckConstraint(
                condition=Q(consentement=True),
                name="enregistrement_avec_consentement",
            ),
        ]

    def __str__(self):
        return f"Enregistrement — {self.activite}"
