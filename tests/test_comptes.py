"""Tests des comptes : utilisateurs, rôles et permissions."""
import pytest
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction

from applications.comptes.models import PermissionMetier, Role

MOT_DE_PASSE = "motdepasse-de-test-123"

Utilisateur = get_user_model()


@pytest.mark.django_db
def test_creation_utilisateur_par_email():
    utilisateur = Utilisateur.objects.create_user(
        email="Awa@Exemple.com", password=MOT_DE_PASSE, nom="Awa"
    )
    assert utilisateur.email == "Awa@exemple.com"
    assert utilisateur.check_password(MOT_DE_PASSE)
    assert utilisateur.statut == "actif"
    assert utilisateur.is_active
    assert not utilisateur.is_staff


@pytest.mark.django_db
def test_email_obligatoire():
    with pytest.raises(ValueError):
        Utilisateur.objects.create_user(email="", password=MOT_DE_PASSE, nom="Sans email")


@pytest.mark.django_db
def test_superutilisateur():
    admin = Utilisateur.objects.create_superuser(
        email="admin@exemple.com", password=MOT_DE_PASSE, nom="Admin"
    )
    assert admin.is_staff
    assert admin.is_superuser


@pytest.mark.django_db
def test_connexion_par_email():
    Utilisateur.objects.create_user(email="moussa@exemple.com", password=MOT_DE_PASSE, nom="Moussa")
    assert authenticate(email="moussa@exemple.com", password=MOT_DE_PASSE) is not None
    assert authenticate(email="moussa@exemple.com", password="mauvais") is None


@pytest.mark.django_db
def test_compte_suspendu_ne_peut_pas_se_connecter():
    utilisateur = Utilisateur.objects.create_user(
        email="fatou@exemple.com", password=MOT_DE_PASSE, nom="Fatou"
    )
    utilisateur.statut = Utilisateur.Statut.SUSPENDU
    utilisateur.save()
    assert not utilisateur.is_active
    assert authenticate(email="fatou@exemple.com", password=MOT_DE_PASSE) is None


@pytest.mark.django_db
def test_roles_et_permissions():
    droit = PermissionMetier.objects.create(
        ressource="Prospects",
        action=PermissionMetier.Action.MODIFIER,
        portee=PermissionMetier.Portee.EQUIPE,
    )
    role = Role.objects.create(nom="Chef d'équipe")
    role.permissions.add(droit)
    utilisateur = Utilisateur.objects.create_user(
        email="ibou@exemple.com", password=MOT_DE_PASSE, nom="Ibou"
    )
    utilisateur.roles.add(role)
    assert role in utilisateur.roles.all()
    assert droit in utilisateur.roles.first().permissions.all()


@pytest.mark.django_db
def test_permission_en_double_refusee():
    PermissionMetier.objects.create(ressource="Contrats", action="V", portee="toute")
    with pytest.raises(IntegrityError), transaction.atomic():
        PermissionMetier.objects.create(ressource="Contrats", action="V", portee="toute")
