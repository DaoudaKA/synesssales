"""Tests des équipes : chef, membres et suppressions."""
import pytest
from django.contrib.auth import get_user_model

from applications.equipes.models import Equipe

MOT_DE_PASSE = "motdepasse-de-test-123"

Utilisateur = get_user_model()


def creer_utilisateur(email, nom):
    return Utilisateur.objects.create_user(email=email, password=MOT_DE_PASSE, nom=nom)


@pytest.mark.django_db
def test_equipe_avec_chef_et_membres():
    chef = creer_utilisateur("chef@exemple.com", "Chef")
    equipe = Equipe.objects.create(nom="Équipe Dakar", chef_equipe=chef)
    commercial = creer_utilisateur("com@exemple.com", "Commercial")
    commercial.equipe = equipe
    commercial.save()
    assert equipe.chef_equipe == chef
    assert commercial in equipe.membres.all()
    assert equipe in chef.equipes_dirigees.all()


@pytest.mark.django_db
def test_suppression_du_chef_conserve_l_equipe():
    chef = creer_utilisateur("chef@exemple.com", "Chef")
    equipe = Equipe.objects.create(nom="Équipe Thiès", chef_equipe=chef)
    chef.delete()
    equipe.refresh_from_db()
    assert equipe.chef_equipe is None


@pytest.mark.django_db
def test_suppression_de_l_equipe_conserve_les_membres():
    equipe = Equipe.objects.create(nom="Équipe Saint-Louis")
    membre = creer_utilisateur("membre@exemple.com", "Membre")
    membre.equipe = equipe
    membre.save()
    equipe.delete()
    membre.refresh_from_db()
    assert membre.equipe is None
