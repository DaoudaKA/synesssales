"""Tests de l'écran des prospects : un écran, des données différentes selon le profil."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def page_prospects(client, email):
    client.force_login(Utilisateur.objects.get(email=email))
    return client.get("/prospects/")


@pytest.mark.django_db
def test_ecran_exige_la_connexion(client):
    reponse = client.get("/prospects/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_commercial_voit_seulement_ses_prospects(client, demo):
    reponse = page_prospects(client, "commercial1@exemple.com")
    contenu = reponse.content.decode()
    assert reponse.status_code == 200
    assert "Garage Baobab" in contenu
    assert "Auto Teranga" in contenu
    assert "Pièces Sahel" not in contenu
    assert "Garage Thiès Centre" not in contenu


@pytest.mark.django_db
def test_chef_d_equipe_voit_son_equipe(client, demo):
    reponse = page_prospects(client, "chef@exemple.com")
    contenu = reponse.content.decode()
    assert reponse.status_code == 200
    assert "Garage Baobab" in contenu
    assert "Pièces Sahel" in contenu
    assert "Garage Thiès Centre" not in contenu
    assert "Casse Auto Rufisque" not in contenu


@pytest.mark.django_db
def test_responsable_data_est_refuse(client, demo):
    reponse = page_prospects(client, "data@exemple.com")
    assert reponse.status_code == 403


@pytest.mark.django_db
def test_lien_prospects_selon_le_profil(client, demo):
    client.force_login(Utilisateur.objects.get(email="commercial1@exemple.com"))
    assert 'href="/prospects/"' in client.get("/").content.decode()
    client.force_login(Utilisateur.objects.get(email="data@exemple.com"))
    assert 'href="/prospects/"' not in client.get("/").content.decode()


@pytest.mark.django_db
def test_donnees_de_demonstration_repetables(demo):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)
    assert Utilisateur.objects.count() == 5
    assert Utilisateur.objects.get(email="chef@exemple.com").equipes_dirigees.count() == 1
