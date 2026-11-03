"""Tests de l'alerte « prospect sans suivi » au chef d'équipe (brique 5)."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.notifications import evenements
from applications.notifications.models import Notification
from applications.notifications.relances import verifier_sans_suivi
from applications.ventes.models import Activite, Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def baobab(demo):
    return Prospect.objects.get(nom="Garage Baobab")


@pytest.fixture
def awa(demo):
    return Utilisateur.objects.get(email="commercial1@exemple.com")


@pytest.fixture
def chef(baobab):
    return baobab.equipe.chef_equipe


def il_y_a(**duree):
    return timezone.now() - datetime.timedelta(**duree)


def vieillir(prospect, **duree):
    """Fait remonter la création du prospect (le champ est rempli automatiquement)."""
    Prospect.objects.filter(pk=prospect.pk).update(date_creation=il_y_a(**duree))


def activite(prospect, auteur, **duree):
    return Activite.objects.create(
        prospect=prospect, auteur=auteur, type="appel", date=il_y_a(**duree)
    )


def alertes_baobab(chef):
    """Alertes « sans suivi » reçues par le chef au sujet de Garage Baobab."""
    return Notification.objects.filter(
        destinataire=chef,
        type=evenements.PROSPECT_SANS_SUIVI,
        message__contains="Garage Baobab",
    )


@pytest.mark.django_db
def test_prospect_sans_activite_depuis_sa_creation_est_signale(baobab, chef):
    vieillir(baobab, days=10)
    verifier_sans_suivi()

    alerte = alertes_baobab(chef).get()
    assert alerte.priorite == Notification.Priorite.MOYENNE
    assert alerte.lien == f"/prospects/{baobab.pk}/"


@pytest.mark.django_db
def test_activite_recente_evite_l_alerte(baobab, awa, chef):
    vieillir(baobab, days=30)
    activite(baobab, awa, days=3)
    verifier_sans_suivi()
    assert not alertes_baobab(chef).exists()


@pytest.mark.django_db
def test_derniere_activite_ancienne_declenche_l_alerte(baobab, awa, chef):
    activite(baobab, awa, days=10)
    assert verifier_sans_suivi()["sans_suivi"] >= 1
    assert alertes_baobab(chef).count() == 1


@pytest.mark.django_db
def test_pas_de_doublon_pour_le_meme_silence(baobab, chef):
    vieillir(baobab, days=10)
    verifier_sans_suivi()
    verifier_sans_suivi()
    assert alertes_baobab(chef).count() == 1


@pytest.mark.django_db
def test_nouvelle_alerte_apres_un_nouveau_silence(baobab, awa, chef):
    activite(baobab, awa, days=20)
    verifier_sans_suivi()
    # Un contact a eu lieu depuis, puis le silence a repris : nouvelle alerte permise.
    activite(baobab, awa, days=9)
    verifier_sans_suivi()
    assert alertes_baobab(chef).count() == 2


@pytest.mark.django_db
def test_prospect_clos_est_ignore(baobab, chef):
    vieillir(baobab, days=10)
    Prospect.objects.filter(pk=baobab.pk).update(statut=Prospect.Statut.GAGNE)
    verifier_sans_suivi()
    assert not alertes_baobab(chef).exists()


@pytest.mark.django_db
def test_le_chef_n_est_pas_alerte_pour_ses_propres_prospects(baobab, chef):
    vieillir(baobab, days=10)
    Prospect.objects.filter(pk=baobab.pk).update(commercial=chef)
    verifier_sans_suivi()
    assert not alertes_baobab(chef).exists()


@pytest.mark.django_db
def test_seuil_parametrable(baobab, chef):
    # Créé à l'instant : avec le seuil par défaut, rien. Avec un seuil de 0, signalé.
    verifier_sans_suivi()
    assert not alertes_baobab(chef).exists()
    verifier_sans_suivi(seuil_jours=0)
    assert alertes_baobab(chef).count() == 1
