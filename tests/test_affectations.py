"""Tests des affectations : transfert sans perte d'historique et écran par profil."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.ventes.models import Affectation, Produit
from applications.ventes.services import affecter

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def commercial(db):
    return Utilisateur.objects.create_user(
        email="com@exemple.com", password=MOT_DE_PASSE, nom="Commercial"
    )


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def page_affectations(client, email):
    client.force_login(Utilisateur.objects.get(email=email))
    return client.get("/affectations/")


@pytest.mark.django_db
def test_premiere_affectation(commercial):
    produit = Produit.objects.create(nom="Garage.sn")
    affectation = affecter(commercial, produit, datetime.date(2026, 7, 1))
    assert affectation.en_cours
    assert commercial.affectations.count() == 1


@pytest.mark.django_db
def test_transfert_conserve_l_historique(commercial):
    ancien = Produit.objects.create(nom="Assurance")
    nouveau = Produit.objects.create(nom="Garage.sn")
    affecter(commercial, ancien, datetime.date(2026, 1, 1))
    affecter(commercial, nouveau, datetime.date(2026, 7, 1))
    assert commercial.affectations.count() == 2
    ancienne = commercial.affectations.get(produit=ancien)
    assert ancienne.date_fin == datetime.date(2026, 6, 30)
    assert not ancienne.en_cours
    assert commercial.affectations.get(produit=nouveau).en_cours


@pytest.mark.django_db
def test_transfert_le_jour_meme(commercial):
    ancien = Produit.objects.create(nom="Assurance")
    nouveau = Produit.objects.create(nom="Garage.sn")
    affecter(commercial, ancien, datetime.date(2026, 7, 1))
    affecter(commercial, nouveau, datetime.date(2026, 7, 1))
    assert commercial.affectations.get(produit=ancien).date_fin == datetime.date(2026, 7, 1)
    assert Affectation.objects.filter(utilisateur=commercial, date_fin__isnull=True).count() == 1


@pytest.mark.django_db
def test_ecran_exige_la_connexion(client):
    reponse = client.get("/affectations/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_commercial_voit_son_historique(client, demo):
    reponse = page_affectations(client, "commercial1@exemple.com")
    contenu = reponse.content.decode()
    assert reponse.status_code == 200
    assert "Assurance auto" in contenu
    assert "Garage.sn" in contenu
    assert "en cours" in contenu
    assert "Awa Diop" in contenu
    assert "Moussa Fall" not in contenu


@pytest.mark.django_db
def test_chef_d_equipe_voit_son_equipe(client, demo):
    contenu = page_affectations(client, "chef@exemple.com").content.decode()
    assert "Awa Diop" in contenu
    assert "Moussa Fall" in contenu
    assert "Fatou Ndiaye" not in contenu


@pytest.mark.django_db
def test_responsable_data_est_refuse(client, demo):
    assert page_affectations(client, "data@exemple.com").status_code == 403


@pytest.mark.django_db
def test_lien_affectations_selon_le_profil(client, demo):
    client.force_login(Utilisateur.objects.get(email="commercial1@exemple.com"))
    assert 'href="/affectations/"' in client.get("/").content.decode()
    client.force_login(Utilisateur.objects.get(email="data@exemple.com"))
    assert 'href="/affectations/"' not in client.get("/").content.decode()
