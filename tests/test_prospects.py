"""Tests des prospects et des affectations."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from applications.equipes.models import Equipe
from applications.partenaires.models import Partenaire
from applications.ventes.models import Affectation, Campagne, Produit, Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def produit(db):
    return Produit.objects.create(nom="Garage.sn")


@pytest.fixture
def commercial(db):
    return Utilisateur.objects.create_user(
        email="com@exemple.com", password=MOT_DE_PASSE, nom="Commercial"
    )


@pytest.mark.django_db
def test_prospect_par_defaut(produit):
    prospect = Prospect.objects.create(nom="Garage Baobab", produit=produit)
    assert prospect.statut == Prospect.Statut.NOUVEAU
    assert prospect.commercial is None
    assert prospect.partenaire is None


@pytest.mark.django_db
def test_prospect_relie_a_un_partenaire_une_equipe_et_un_commercial(produit, commercial):
    partenaire = Partenaire.objects.create(nom_commercial="Garage Baobab")
    equipe = Equipe.objects.create(nom="Équipe Dakar")
    campagne = Campagne.objects.create(
        nom="Lancement", produit=produit, date_debut=datetime.date(2026, 11, 1)
    )
    prospect = Prospect.objects.create(
        nom="Garage Baobab",
        produit=produit,
        partenaire=partenaire,
        commercial=commercial,
        equipe=equipe,
        campagne=campagne,
    )
    assert prospect in commercial.prospects_suivis.all()
    assert prospect in equipe.prospects.all()
    assert prospect in partenaire.prospects.all()
    assert prospect in campagne.prospects.all()


@pytest.mark.django_db
def test_depart_du_commercial_conserve_le_prospect(produit, commercial):
    prospect = Prospect.objects.create(nom="Garage Baobab", produit=produit, commercial=commercial)
    commercial.delete()
    prospect.refresh_from_db()
    assert prospect.commercial is None


@pytest.mark.django_db
def test_produit_avec_prospect_ne_peut_pas_etre_supprime(produit):
    Prospect.objects.create(nom="Garage Baobab", produit=produit)
    with pytest.raises(ProtectedError):
        produit.delete()


@pytest.mark.django_db
def test_affectation_en_cours_puis_terminee(produit, commercial):
    affectation = Affectation.objects.create(
        utilisateur=commercial, produit=produit, date_debut=datetime.date(2026, 11, 1)
    )
    assert affectation.en_cours
    affectation.date_fin = datetime.date(2026, 12, 1)
    affectation.save()
    assert not affectation.en_cours


@pytest.mark.django_db
def test_historique_des_affectations_apres_transfert(commercial):
    ancien = Produit.objects.create(nom="Assurance")
    nouveau = Produit.objects.create(nom="Garage.sn")
    Affectation.objects.create(
        utilisateur=commercial,
        produit=ancien,
        date_debut=datetime.date(2026, 1, 1),
        date_fin=datetime.date(2026, 6, 30),
    )
    Affectation.objects.create(
        utilisateur=commercial, produit=nouveau, date_debut=datetime.date(2026, 7, 1)
    )
    assert commercial.affectations.count() == 2
    assert commercial.affectations.filter(date_fin__isnull=True).get().produit == nouveau


@pytest.mark.django_db
def test_affectation_refuse_une_fin_avant_le_debut(produit, commercial):
    with pytest.raises(IntegrityError), transaction.atomic():
        Affectation.objects.create(
            utilisateur=commercial,
            produit=produit,
            date_debut=datetime.date(2026, 12, 1),
            date_fin=datetime.date(2026, 11, 1),
        )
