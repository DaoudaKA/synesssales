"""Tests du socle : le projet démarre et la base répond."""
import pytest
from django.conf import settings
from django.db import connection


def test_reglages_de_developpement_charges():
    assert settings.SETTINGS_MODULE == "configuration.parametres.dev"


def test_fuseau_horaire_et_langue():
    assert settings.TIME_ZONE == "Africa/Dakar"
    assert settings.LANGUAGE_CODE == "fr-fr"


@pytest.mark.django_db
def test_connexion_postgresql():
    with connection.cursor() as curseur:
        curseur.execute("SELECT 1;")
        assert curseur.fetchone() == (1,)
def test_adresse_sante(client):
    reponse = client.get("/sante/")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}
