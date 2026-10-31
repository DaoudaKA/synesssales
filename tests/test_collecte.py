"""Tests de la collecte : sources, provenance, vérifications et doublons."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from applications.collecte.models import (
    AlerteDoublon,
    Collecte,
    Provenance,
    SourceDonnees,
    Verification,
)
from applications.partenaires.models import Partenaire

Utilisateur = get_user_model()


@pytest.fixture
def source(db):
    return SourceDonnees.objects.create(nom="Annuaire public", type="site")


@pytest.fixture
def partenaire(db):
    return Partenaire.objects.create(nom_commercial="Garage Teranga")


@pytest.mark.django_db
def test_source_non_validee_par_defaut(source):
    assert source.conditions_validees is False


@pytest.mark.django_db
def test_provenance_par_defaut_inconnue(source, partenaire):
    provenance = Provenance.objects.create(
        partenaire=partenaire,
        source=source,
        champ="telephone",
        valeur="+221 77 000 00 00",
        date_collecte=timezone.now(),
    )
    assert provenance.niveau == Provenance.Niveau.INCONNU
    assert provenance.collecte is None


@pytest.mark.django_db
def test_collecte_et_provenance(source, partenaire):
    collecte = Collecte.objects.create(source=source, date_debut=timezone.now())
    Provenance.objects.create(
        partenaire=partenaire,
        source=source,
        collecte=collecte,
        champ="ville",
        valeur="Dakar",
        date_collecte=timezone.now(),
        niveau=Provenance.Niveau.COLLECTE,
    )
    assert collecte.statut == Collecte.Statut.EN_COURS
    assert collecte.provenances.count() == 1
    assert partenaire.provenances.first().valeur == "Dakar"


@pytest.mark.django_db
def test_source_utilisee_ne_peut_pas_etre_supprimee(source, partenaire):
    Provenance.objects.create(
        partenaire=partenaire,
        source=source,
        champ="ville",
        date_collecte=timezone.now(),
    )
    with pytest.raises(ProtectedError):
        source.delete()


@pytest.mark.django_db
def test_verification_enregistre_l_utilisateur(partenaire):
    controleur = Utilisateur.objects.create_user(
        email="data@exemple.com", password="motdepasse-de-test-123", nom="Data"
    )
    verification = Verification.objects.create(
        partenaire=partenaire,
        utilisateur=controleur,
        resultat=Verification.Resultat.CONFORME,
    )
    assert verification in controleur.verifications.all()
    assert verification.date is not None


@pytest.mark.django_db
def test_alerte_doublon_entre_deux_fiches(partenaire):
    autre = Partenaire.objects.create(nom_commercial="Garage Téranga")
    alerte = AlerteDoublon.objects.create(
        partenaire_a=partenaire, partenaire_b=autre, score_similarite=0.92
    )
    assert alerte.statut == AlerteDoublon.Statut.OUVERTE
    assert alerte in partenaire.alertes_doublon_a.all()


@pytest.mark.django_db
def test_alerte_doublon_refuse_une_fiche_avec_elle_meme(partenaire):
    with pytest.raises(IntegrityError), transaction.atomic():
        AlerteDoublon.objects.create(
            partenaire_a=partenaire, partenaire_b=partenaire, score_similarite=1.0
        )


@pytest.mark.django_db
def test_alerte_doublon_en_double_refusee(partenaire):
    autre = Partenaire.objects.create(nom_commercial="Autre garage")
    AlerteDoublon.objects.create(
        partenaire_a=partenaire, partenaire_b=autre, score_similarite=0.8
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        AlerteDoublon.objects.create(
            partenaire_a=partenaire, partenaire_b=autre, score_similarite=0.8
        )
