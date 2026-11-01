"""Tests de la saisie d'une fiche partenaire."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.comptes.models import JournalAudit
from applications.partenaires.models import Partenaire

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"
DONNEES = {
    "nom_commercial": "Garage Nouveau",
    "pays": "Sénégal",
    "ville": "Saint-Louis",
    "telephone": "+221 77 000 00 00",
    "email": "contact@garage-nouveau.sn",
    "service": "Vidange",
}


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def se_connecter(client, email):
    utilisateur = Utilisateur.objects.get(email=email)
    client.force_login(utilisateur)
    return utilisateur


@pytest.mark.django_db
def test_ecran_exige_la_connexion(client):
    reponse = client.get("/partenaires/nouveau/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_commercial_ne_peut_pas_creer(client, demo):
    se_connecter(client, "commercial1@exemple.com")
    assert client.get("/partenaires/nouveau/").status_code == 403
    assert client.post("/partenaires/nouveau/", DONNEES).status_code == 403
    assert not Partenaire.objects.filter(nom_commercial="Garage Nouveau").exists()


@pytest.mark.django_db
def test_responsable_data_voit_le_formulaire(client, demo):
    se_connecter(client, "data@exemple.com")
    assert client.get("/partenaires/nouveau/").status_code == 200


@pytest.mark.django_db
def test_creation_complete(client, demo):
    se_connecter(client, "data@exemple.com")
    reponse = client.post("/partenaires/nouveau/", DONNEES)
    assert reponse.status_code == 302
    assert reponse.url.startswith("/partenaires/")
    partenaire = Partenaire.objects.get(nom_commercial="Garage Nouveau")
    assert partenaire.statut_verification == Partenaire.StatutVerification.A_VERIFIER
    assert partenaire.localisations.get().ville == "Saint-Louis"
    assert partenaire.contacts.count() == 2
    assert partenaire.services.get().libelle == "Vidange"


@pytest.mark.django_db
def test_creation_est_journalisee(client, demo):
    utilisateur = se_connecter(client, "data@exemple.com")
    client.post("/partenaires/nouveau/", DONNEES)
    partenaire = Partenaire.objects.get(nom_commercial="Garage Nouveau")
    assert JournalAudit.objects.filter(
        utilisateur=utilisateur,
        action="creation",
        ressource="Fiches partenaires",
        objet_id=str(partenaire.pk),
    ).exists()


@pytest.mark.django_db
def test_nom_obligatoire(client, demo):
    se_connecter(client, "data@exemple.com")
    reponse = client.post("/partenaires/nouveau/", {**DONNEES, "nom_commercial": ""})
    assert reponse.status_code == 200
    assert not Partenaire.objects.filter(localisations__ville="Saint-Louis").exists()


@pytest.mark.django_db
def test_email_invalide_refuse(client, demo):
    se_connecter(client, "data@exemple.com")
    reponse = client.post("/partenaires/nouveau/", {**DONNEES, "email": "pas-un-email"})
    assert reponse.status_code == 200
    assert not Partenaire.objects.filter(nom_commercial="Garage Nouveau").exists()


@pytest.mark.django_db
def test_bouton_nouvelle_fiche_selon_le_profil(client, demo):
    se_connecter(client, "data@exemple.com")
    assert 'href="/partenaires/nouveau/"' in client.get("/partenaires/").content.decode()
    se_connecter(client, "commercial1@exemple.com")
    assert 'href="/partenaires/nouveau/"' not in client.get("/partenaires/").content.decode()
