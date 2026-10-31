"""Modèles des comptes : utilisateurs, rôles et permissions (annexe E.2)."""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class PermissionMetier(models.Model):
    """Un droit : une action sur une ressource, dans une portée donnée."""

    class Action(models.TextChoices):
        CONSULTER = "L", "Consulter"
        CREER = "C", "Créer"
        MODIFIER = "M", "Modifier"
        VALIDER = "V", "Valider"
        SUPPRIMER = "S", "Supprimer"
        EXPORTER = "E", "Exporter"
        ADMINISTRER = "A", "Administrer"

    class Portee(models.TextChoices):
        TOUTE = "toute", "Tout le périmètre"
        EQUIPE = "equipe", "Son équipe"
        PRODUIT = "produit", "Ses produits"
        ZONE = "zone", "Sa zone"
        PROPRE = "propre", "Ses propres données"

    ressource = models.CharField(max_length=80)
    action = models.CharField(max_length=1, choices=Action.choices)
    portee = models.CharField(max_length=10, choices=Portee.choices, default=Portee.TOUTE)

    class Meta:
        verbose_name = "permission métier"
        verbose_name_plural = "permissions métier"
        constraints = [
            models.UniqueConstraint(
                fields=["ressource", "action", "portee"], name="permission_unique"
            ),
        ]

    def __str__(self):
        return f"{self.ressource} : {self.get_action_display()} ({self.get_portee_display()})"


class Role(models.Model):
    """Un profil (Direction, Commercial...) qui regroupe des permissions."""

    nom = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        PermissionMetier, blank=True, related_name="roles"
    )

    class Meta:
        verbose_name = "rôle"
        verbose_name_plural = "rôles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class GestionnaireUtilisateur(BaseUserManager):
    """Crée les utilisateurs avec l'e-mail comme identifiant."""

    use_in_migrations = True

    def _creer(self, email, password, **extra):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        utilisateur = self.model(email=self.normalize_email(email), **extra)
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._creer(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._creer(email, password, **extra)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Compte d'une personne : connexion par e-mail, un ou plusieurs rôles."""

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"

    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=150)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF)
    roles = models.ManyToManyField(Role, blank=True, related_name="utilisateurs")
    equipe = models.ForeignKey(
        "equipes.Equipe",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="membres",
    )
    is_staff = models.BooleanField("accès à l'administration", default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    objects = GestionnaireUtilisateur()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom"]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["nom"]

    @property
    def is_active(self):
        """Un compte suspendu ne peut plus se connecter."""
        return self.statut == self.Statut.ACTIF

    def __str__(self):
        return f"{self.nom} <{self.email}>"


class JournalAudit(models.Model):
    """Trace d'une action sensible : qui, quand, quoi, sur quel objet.

    Une entrée ne se modifie ni ne se supprime jamais.
    """

    utilisateur = models.ForeignKey(
        Utilisateur,
        null=True,
        on_delete=models.SET_NULL,
        related_name="actions_journalisees",
    )
    action = models.CharField(max_length=80)
    ressource = models.CharField(max_length=120)
    objet_id = models.CharField(max_length=64, blank=True)
    detail = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "entrée du journal d'audit"
        verbose_name_plural = "journal d'audit"
        ordering = ["-date"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Une entrée du journal d'audit ne se modifie pas.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Une entrée du journal d'audit ne se supprime pas.")

    def __str__(self):
        return f"{self.date:%d/%m/%Y %H:%M} — {self.action} — {self.ressource}"
