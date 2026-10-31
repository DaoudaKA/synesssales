"""Tests des ventes : produits, campagnes et scripts."""
import datetime

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from applications.equipes.models import Equipe
from applications.ventes.models import Campagne, Produit, Script


@pytest.fixture
def produit(db):
    return Produit.objects.create(nom="Garage.sn")


@pytest.mark.django_db
def test_produit_par_defaut(produit):
    assert produit.statut == Produit.Statut.ACTIF
    assert produit.argumentaire_valide is False
    assert str(produit) == "Garage.sn"


@pytest.mark.django_db
def test_equipe_responsable_du_produit():
    equipe = Equipe.objects.create(nom="Équipe Dakar")
    produit = Produit.objects.create(nom="Garage.sn", equipe_responsable=equipe)
    assert produit in equipe.produits.all()
    equipe.delete()
    produit.refresh_from_db()
    assert produit.equipe_responsable is None


@pytest.mark.django_db
def test_campagne_d_un_produit(produit):
    campagne = Campagne.objects.create(
        nom="Lancement Dakar",
        produit=produit,
        zone="Dakar",
        date_debut=datetime.date(2026, 11, 1),
        date_fin=datetime.date(2026, 12, 31),
    )
    assert campagne in produit.campagnes.all()


@pytest.mark.django_db
def test_campagne_refuse_une_fin_avant_le_debut(produit):
    with pytest.raises(IntegrityError), transaction.atomic():
        Campagne.objects.create(
            nom="Dates incohérentes",
            produit=produit,
            date_debut=datetime.date(2026, 12, 31),
            date_fin=datetime.date(2026, 11, 1),
        )


@pytest.mark.django_db
def test_produit_avec_campagne_ne_peut_pas_etre_supprime(produit):
    Campagne.objects.create(
        nom="Lancement", produit=produit, date_debut=datetime.date(2026, 11, 1)
    )
    with pytest.raises(ProtectedError):
        produit.delete()


@pytest.mark.django_db
def test_script_brouillon_par_defaut_et_version_unique(produit):
    script = Script.objects.create(produit=produit, contenu="Bonjour, je vous appelle...")
    assert script.statut_validation == Script.StatutValidation.BROUILLON
    assert script.version == 1
    with pytest.raises(IntegrityError), transaction.atomic():
        Script.objects.create(produit=produit, version=1, contenu="Autre texte")


@pytest.mark.django_db
def test_scripts_supprimes_avec_le_produit(produit):
    Script.objects.create(produit=produit, contenu="Texte")
    produit.delete()
    assert Script.objects.count() == 0
