"""Tests du journal d'audit : enregistrement, administration et lecture seule."""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from applications.comptes.models import JournalAudit, PermissionMetier, Role
from applications.comptes.services import journaliser
from applications.partenaires.models import Partenaire

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def admin(db):
    return Utilisateur.objects.create_superuser(
        email="admin@exemple.com", password=MOT_DE_PASSE, nom="Admin"
    )


@pytest.mark.django_db
def test_journaliser_enregistre_l_auteur(admin):
    entree = journaliser(admin, "export", "Partenaires", 12, "Export de 120 fiches")
    assert entree.utilisateur == admin
    assert entree.objet_id == "12"
    assert entree.date is not None


@pytest.mark.django_db
def test_journaliser_sans_utilisateur_connecte():
    entree = journaliser(AnonymousUser(), "export", "Partenaires")
    assert entree.utilisateur is None


@pytest.mark.django_db
def test_suppression_dans_l_administration_est_journalisee(client, admin):
    partenaire = Partenaire.objects.create(nom_commercial="Garage Test")
    client.force_login(admin)
    reponse = client.post(
        f"/admin/partenaires/partenaire/{partenaire.pk}/delete/", {"post": "yes"}
    )
    assert reponse.status_code == 302
    assert not Partenaire.objects.filter(pk=partenaire.pk).exists()
    entree = JournalAudit.objects.get(action="suppression", objet_id=str(partenaire.pk))
    assert entree.utilisateur == admin
    assert "Garage Test" in entree.detail


@pytest.mark.django_db
def test_modification_d_un_role_est_journalisee(client, admin):
    role = Role.objects.create(nom="Test")
    droit = PermissionMetier.objects.create(ressource="Contrats", action="L", portee="toute")
    client.force_login(admin)
    reponse = client.post(
        f"/admin/comptes/role/{role.pk}/change/",
        {"nom": "Test", "description": "", "permissions": [droit.pk]},
    )
    assert reponse.status_code == 302
    assert JournalAudit.objects.filter(
        action="modification_droits", ressource="Rôles", objet_id=str(role.pk)
    ).exists()


@pytest.mark.django_db
def test_journal_en_lecture_seule_dans_l_administration(client, admin):
    entree = journaliser(admin, "export", "Partenaires")
    client.force_login(admin)
    assert client.post(f"/admin/comptes/journalaudit/{entree.pk}/change/", {}).status_code == 403
    suppression = client.post(
        f"/admin/comptes/journalaudit/{entree.pk}/delete/", {"post": "yes"}
    )
    assert suppression.status_code == 403
    assert JournalAudit.objects.filter(pk=entree.pk).exists()
