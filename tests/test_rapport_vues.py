"""Tests des écrans de collecte : liste enrichie et rapport."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from applications.collecte.models import SourceDonnees
from applications.collecte.services import traiter_lignes

Utilisateur = get_user_model()


@pytest.fixture
def data(db):
    # La démo crée les rôles et les comptes (même méthode que test_sources.py).
    call_command("charger_demo", "--mot-de-passe", "daouda")
    return Utilisateur.objects.get(email="data@exemple.com")


@pytest.fixture
def collecte(db):
    source = SourceDonnees.objects.create(nom="Source de rapport", conditions_validees=True)
    lignes = [
        {"nom_commercial": "Atelier Rapport", "ville": "Dakar"},
        {"ville": "Thiès"},  # nom manquant : rejetée
    ]
    return traiter_lignes(lignes, source)[0]


@pytest.mark.django_db
def test_rapport_affiche_compteurs_et_lignes_rejetees(client, data, collecte):
    client.force_login(data)
    reponse = client.get(reverse("collecte_rapport", args=[collecte.pk]))
    assert reponse.status_code == 200
    contenu = reponse.content.decode()
    assert "Source de rapport" in contenu
    assert "Nom commercial manquant" in contenu  # motif du rejet
    assert "50 %" in contenu  # 1 rejetée sur 2 lignes traitées


@pytest.mark.django_db
def test_rapport_inconnu_donne_404(client, data):
    client.force_login(data)
    assert client.get(reverse("collecte_rapport", args=[99999])).status_code == 404


@pytest.mark.django_db
def test_rapport_exige_une_connexion(client, collecte):
    reponse = client.get(reverse("collecte_rapport", args=[collecte.pk]))
    assert reponse.status_code == 302  # redirigé vers la connexion


@pytest.mark.django_db
def test_liste_affiche_les_compteurs_et_le_lien_du_rapport(client, data, collecte):
    client.force_login(data)
    contenu = client.get(reverse("collectes")).content.decode()
    assert "Source de rapport" in contenu
    assert reverse("collecte_rapport", args=[collecte.pk]) in contenu
