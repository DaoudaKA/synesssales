"""Tests de la visibilité des prospects selon le rôle."""
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from applications.comptes.matrice import charger_matrice
from applications.comptes.models import Role
from applications.equipes.models import Equipe
from applications.ventes.models import Produit, Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


def creer(email, role=None, equipe=None):
    utilisateur = Utilisateur.objects.create_user(
        email=email, password=MOT_DE_PASSE, nom=email, equipe=equipe
    )
    if role:
        utilisateur.roles.add(Role.objects.get(nom=role))
    return utilisateur


def noms(queryset):
    return sorted(queryset.values_list("nom", flat=True))


@pytest.fixture
def monde(db):
    charger_matrice()
    produit = Produit.objects.create(nom="Garage.sn")
    equipe_a = Equipe.objects.create(nom="Équipe A")
    equipe_b = Equipe.objects.create(nom="Équipe B")
    commercial_a1 = creer("a1@exemple.com", "Commercial", equipe_a)
    commercial_a2 = creer("a2@exemple.com", "Commercial", equipe_a)
    commercial_b1 = creer("b1@exemple.com", "Commercial", equipe_b)
    chef_a = creer("chef@exemple.com", "Chef d'équipe")
    equipe_a.chef_equipe = chef_a
    equipe_a.save()
    Prospect.objects.create(nom="P1", produit=produit, commercial=commercial_a1, equipe=equipe_a)
    Prospect.objects.create(nom="P2", produit=produit, commercial=commercial_a2, equipe=equipe_a)
    Prospect.objects.create(nom="P3", produit=produit, commercial=commercial_b1, equipe=equipe_b)
    Prospect.objects.create(nom="P4", produit=produit)
    return SimpleNamespace(
        equipe_a=equipe_a,
        equipe_b=equipe_b,
        commercial_a1=commercial_a1,
        chef_a=chef_a,
    )


@pytest.mark.django_db
def test_commercial_ne_voit_que_ses_prospects(monde):
    assert noms(Prospect.objects.visible_to(monde.commercial_a1)) == ["P1"]


@pytest.mark.django_db
def test_chef_d_equipe_voit_son_equipe(monde):
    assert noms(Prospect.objects.visible_to(monde.chef_a)) == ["P1", "P2"]


@pytest.mark.django_db
def test_direction_voit_tout(monde):
    direction = creer("direction@exemple.com", "Direction")
    assert noms(Prospect.objects.visible_to(direction)) == ["P1", "P2", "P3", "P4"]


@pytest.mark.django_db
def test_responsable_data_ne_voit_aucun_prospect(monde):
    responsable = creer("data@exemple.com", "Responsable data")
    assert noms(Prospect.objects.visible_to(responsable)) == []


@pytest.mark.django_db
def test_utilisateur_sans_role_ne_voit_rien(monde):
    inconnu = creer("inconnu@exemple.com")
    assert noms(Prospect.objects.visible_to(inconnu)) == []


@pytest.mark.django_db
def test_lecteur_sans_equipe_ne_voit_pas_les_prospects_sans_equipe(monde):
    lecteur = creer("lecteur@exemple.com", "Lecteur autorisé")
    assert noms(Prospect.objects.visible_to(lecteur)) == []


@pytest.mark.django_db
def test_lecteur_voit_les_prospects_de_son_equipe(monde):
    lecteur = creer("lecteur@exemple.com", "Lecteur autorisé", monde.equipe_b)
    assert noms(Prospect.objects.visible_to(lecteur)) == ["P3"]
