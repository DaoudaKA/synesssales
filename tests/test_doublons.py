"""Tests de la détection des doublons de fiches partenaires."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.collecte.models import AlerteDoublon
from applications.partenaires.models import Localisation, Partenaire
from applications.partenaires.services import detecter_doublons, normaliser, similarite

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


def creer(nom, ville=""):
    fiche = Partenaire.objects.create(nom_commercial=nom)
    Localisation.objects.create(partenaire=fiche, pays="Sénégal", ville=ville)
    return fiche


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def se_connecter(client, email):
    client.force_login(Utilisateur.objects.get(email=email))


def test_normaliser_retire_accents_et_ponctuation():
    assert normaliser("  Garage  Téranga, S.A. ") == "garage teranga s a"
    assert similarite("Garage Téranga", "garage teranga") == 1.0


@pytest.mark.django_db
def test_noms_proches_dans_la_meme_ville_donnent_une_alerte():
    ancienne = creer("Garage Teranga", "Dakar")
    nouvelle = creer("Garage Téranga", "dakar")
    alertes = detecter_doublons(nouvelle)
    assert len(alertes) == 1
    assert alertes[0].partenaire_a == ancienne
    assert alertes[0].partenaire_b == nouvelle
    assert alertes[0].score_similarite >= 0.85
    assert alertes[0].statut == AlerteDoublon.Statut.OUVERTE


@pytest.mark.django_db
def test_villes_differentes_pas_d_alerte():
    creer("Garage Teranga", "Dakar")
    assert detecter_doublons(creer("Garage Teranga", "Thiès")) == []


@pytest.mark.django_db
def test_noms_differents_pas_d_alerte():
    creer("Garage Teranga", "Dakar")
    assert detecter_doublons(creer("Carrosserie Almadies", "Dakar")) == []


@pytest.mark.django_db
def test_detection_repetee_ne_cree_pas_de_second_doublon():
    creer("Garage Teranga", "Dakar")
    nouvelle = creer("Garage Teranga", "Dakar")
    assert len(detecter_doublons(nouvelle)) == 1
    assert detecter_doublons(nouvelle) == []
    assert AlerteDoublon.objects.count() == 1


@pytest.mark.django_db
def test_creation_par_formulaire_redirige_vers_les_doublons(client, demo):
    se_connecter(client, "data@exemple.com")
    reponse = client.post(
        "/partenaires/nouveau/",
        {"nom_commercial": "Garage Téranga", "pays": "Sénégal", "ville": "Dakar"},
    )
    assert reponse.status_code == 302
    assert reponse.url == "/partenaires/doublons/"
    assert AlerteDoublon.objects.count() == 1


@pytest.mark.django_db
def test_ecran_doublons_pour_le_responsable_data(client, demo):
    creer("Garage Teranga", "Dakar")
    detecter_doublons(creer("Garage Téranga", "Dakar"))
    se_connecter(client, "data@exemple.com")
    reponse = client.get("/partenaires/doublons/")
    assert reponse.status_code == 200
    assert "Garage Téranga" in reponse.content.decode()


@pytest.mark.django_db
def test_ecran_doublons_refuse_au_commercial(client, demo):
    se_connecter(client, "commercial1@exemple.com")
    assert client.get("/partenaires/doublons/").status_code == 403


@pytest.mark.django_db
def test_ecran_doublons_exige_la_connexion(client):
    reponse = client.get("/partenaires/doublons/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")
