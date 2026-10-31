"""Tests de la connexion par e-mail et de la page d'accueil."""
import pytest
from django.contrib.auth import get_user_model

from applications.comptes.matrice import charger_matrice
from applications.comptes.models import Role

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def commercial(db):
    charger_matrice()
    utilisateur = Utilisateur.objects.create_user(
        email="awa@exemple.com", password=MOT_DE_PASSE, nom="Awa Diop"
    )
    utilisateur.roles.add(Role.objects.get(nom="Commercial"))
    return utilisateur


@pytest.mark.django_db
def test_page_de_connexion_accessible(client):
    reponse = client.get("/connexion/")
    assert reponse.status_code == 200


@pytest.mark.django_db
def test_connexion_reussie_puis_accueil(client, commercial):
    reponse = client.post(
        "/connexion/", {"username": "awa@exemple.com", "password": MOT_DE_PASSE}
    )
    assert reponse.status_code == 302
    assert reponse.url == "/"
    accueil = client.get("/")
    contenu = accueil.content.decode()
    assert accueil.status_code == 200
    assert "Awa Diop" in contenu
    assert "Commercial" in contenu


@pytest.mark.django_db
def test_mauvais_mot_de_passe_refuse(client, commercial):
    reponse = client.post(
        "/connexion/", {"username": "awa@exemple.com", "password": "mauvais"}
    )
    assert reponse.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_compte_suspendu_ne_peut_pas_se_connecter(client, commercial):
    commercial.statut = Utilisateur.Statut.SUSPENDU
    commercial.save()
    client.post("/connexion/", {"username": "awa@exemple.com", "password": MOT_DE_PASSE})
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_accueil_exige_la_connexion(client):
    reponse = client.get("/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_deconnexion(client, commercial):
    client.force_login(commercial)
    reponse = client.post("/deconnexion/")
    assert reponse.status_code == 302
    assert client.get("/").status_code == 302
