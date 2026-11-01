"""Tests de la liste des partenaires : droits, recherche et filtre."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def page(client, email, **parametres):
    client.force_login(Utilisateur.objects.get(email=email))
    return client.get("/partenaires/", parametres)


@pytest.mark.django_db
def test_ecran_exige_la_connexion(client):
    reponse = client.get("/partenaires/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_utilisateur_sans_role_est_refuse(client):
    utilisateur = Utilisateur.objects.create_user(
        email="sans-role@exemple.com", password=MOT_DE_PASSE, nom="Sans rôle"
    )
    client.force_login(utilisateur)
    assert client.get("/partenaires/").status_code == 403


@pytest.mark.django_db
def test_commercial_voit_toutes_les_fiches(client, demo):
    reponse = page(client, "commercial1@exemple.com")
    contenu = reponse.content.decode()
    assert reponse.status_code == 200
    assert "Garage Teranga" in contenu
    assert "Auto Service Thiès" in contenu
    assert "Carrosserie Almadies" in contenu


@pytest.mark.django_db
def test_responsable_data_voit_les_fiches(client, demo):
    assert "Garage Teranga" in page(client, "data@exemple.com").content.decode()


@pytest.mark.django_db
def test_recherche_par_ville(client, demo):
    contenu = page(client, "chef@exemple.com", q="Thiès").content.decode()
    assert "Auto Service Thiès" in contenu
    assert "Garage Teranga" not in contenu


@pytest.mark.django_db
def test_recherche_par_categorie_sans_doublon(client, demo):
    contenu = page(client, "chef@exemple.com", q="garage").content.decode()
    assert contenu.count("Garage Teranga") == 1


@pytest.mark.django_db
def test_filtre_par_statut_de_verification(client, demo):
    contenu = page(client, "chef@exemple.com", statut="verifie").content.decode()
    assert "Garage Teranga" in contenu
    assert "Auto Service Thiès" not in contenu


@pytest.mark.django_db
def test_lien_partenaires_sur_l_accueil(client, demo):
    client.force_login(Utilisateur.objects.get(email="commercial1@exemple.com"))
    assert 'href="/partenaires/"' in client.get("/").content.decode()
