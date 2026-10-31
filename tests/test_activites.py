"""Tests des activités, tâches, contrats et enregistrements vocaux."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from applications.ventes.models import (
    Activite,
    Contrat,
    EnregistrementVocal,
    Produit,
    Prospect,
    Script,
    Tache,
)

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def commercial(db):
    return Utilisateur.objects.create_user(
        email="com@exemple.com", password=MOT_DE_PASSE, nom="Commercial"
    )


@pytest.fixture
def prospect(db):
    produit = Produit.objects.create(nom="Garage.sn")
    return Prospect.objects.create(nom="Garage Baobab", produit=produit)


@pytest.mark.django_db
def test_historique_des_activites(prospect, commercial):
    Activite.objects.create(
        prospect=prospect,
        auteur=commercial,
        type=Activite.Type.APPEL,
        date=timezone.now(),
        duree_minutes=12,
        objections="Trop cher",
    )
    assert prospect.activites.count() == 1
    assert prospect.activites.first().auteur == commercial


@pytest.mark.django_db
def test_historique_conserve_apres_depart_du_commercial(prospect, commercial):
    activite = Activite.objects.create(
        prospect=prospect, auteur=commercial, type="visite", date=timezone.now()
    )
    commercial.delete()
    activite.refresh_from_db()
    assert activite.auteur is None


@pytest.mark.django_db
def test_activite_utilisant_un_script(prospect):
    script = Script.objects.create(produit=prospect.produit, contenu="Bonjour...")
    activite = Activite.objects.create(
        prospect=prospect, type="appel", date=timezone.now(), script=script
    )
    assert activite in script.activites.all()


@pytest.mark.django_db
def test_tache_a_faire_par_defaut(prospect, commercial):
    tache = Tache.objects.create(
        prospect=prospect,
        responsable=commercial,
        type=Tache.Type.RELANCE,
        echeance=timezone.now() + datetime.timedelta(days=3),
    )
    assert tache.statut == Tache.Statut.A_FAIRE
    assert tache in commercial.taches.all()


@pytest.mark.django_db
def test_contrat_soumis_puis_valide(prospect, commercial):
    contrat = Contrat.objects.create(prospect=prospect)
    assert contrat.statut_validation == Contrat.StatutValidation.SOUMIS
    contrat.statut_validation = Contrat.StatutValidation.VALIDE
    contrat.valide_par = commercial
    contrat.save()
    assert contrat in commercial.contrats_valides.all()


@pytest.mark.django_db
def test_prospect_avec_contrat_ne_peut_pas_etre_supprime(prospect):
    Contrat.objects.create(prospect=prospect)
    with pytest.raises(ProtectedError):
        prospect.delete()


@pytest.mark.django_db
def test_enregistrement_avec_consentement(prospect, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    activite = Activite.objects.create(prospect=prospect, type="appel", date=timezone.now())
    enregistrement = EnregistrementVocal.objects.create(
        activite=activite,
        fichier=ContentFile(b"audio", name="appel.mp3"),
        consentement=True,
    )
    assert activite.enregistrement == enregistrement


@pytest.mark.django_db
def test_enregistrement_sans_consentement_refuse(prospect, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    activite = Activite.objects.create(prospect=prospect, type="appel", date=timezone.now())
    with pytest.raises(IntegrityError), transaction.atomic():
        EnregistrementVocal.objects.create(
            activite=activite,
            fichier=ContentFile(b"audio", name="appel.mp3"),
            consentement=False,
        )
