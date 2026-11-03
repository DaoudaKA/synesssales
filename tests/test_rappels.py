"""Tests des rappels d'échéance et des rendez-vous imminents (brique 5)."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.notifications import evenements
from applications.notifications.models import Notification
from applications.notifications.relances import verifier_rappels, verifier_relances
from applications.ventes.models import Prospect, Tache

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


def dans(**duree):
    return timezone.now() + datetime.timedelta(**duree)


def tache(baobab, responsable, type_, **duree):
    """Une tâche à faire dont l'échéance est dans la durée donnée."""
    return Tache.objects.create(
        prospect=baobab, responsable=responsable, type=type_, echeance=dans(**duree)
    )


def recues(utilisateur, type_):
    return Notification.objects.filter(destinataire=utilisateur, type=type_)


@pytest.mark.django_db
def test_echeance_proche_declenche_un_rappel_haute_priorite(baobab, awa):
    tache(baobab, awa, "relance", hours=3)
    bilan = verifier_rappels()

    assert bilan["relances_a_echeance"] == 1
    rappel = recues(awa, evenements.RELANCE_A_ECHEANCE).get()
    assert rappel.priorite == Notification.Priorite.HAUTE
    assert rappel.lien == f"/prospects/{baobab.pk}/"


@pytest.mark.django_db
def test_echeance_lointaine_ne_declenche_rien(baobab, awa):
    tache(baobab, awa, "relance", days=3)
    assert verifier_rappels()["relances_a_echeance"] == 0
    assert not Notification.objects.filter(type=evenements.RELANCE_A_ECHEANCE).exists()


@pytest.mark.django_db
def test_rendez_vous_imminent(baobab, awa):
    tache(baobab, awa, "rdv", hours=1)
    bilan = verifier_rappels()

    assert bilan["rdv_imminents"] == 1 and bilan["relances_a_echeance"] == 0
    assert recues(awa, evenements.RDV_IMMINENT).get().priorite == Notification.Priorite.HAUTE


@pytest.mark.django_db
def test_rendez_vous_trop_lointain_n_est_pas_imminent(baobab, awa):
    # Dans 5 heures : au-delà du délai de 2 heures, et un rendez-vous n'est jamais
    # traité comme une simple échéance.
    tache(baobab, awa, "rdv", hours=5)
    bilan = verifier_rappels()
    assert bilan["rdv_imminents"] == 0 and bilan["relances_a_echeance"] == 0


@pytest.mark.django_db
def test_rappels_sans_doublon(baobab, awa):
    tache(baobab, awa, "relance", hours=3)
    tache(baobab, awa, "rdv", hours=1)
    verifier_rappels()
    second = verifier_rappels()

    assert second["relances_a_echeance"] == 0 and second["rdv_imminents"] == 0
    assert recues(awa, evenements.RELANCE_A_ECHEANCE).count() == 1
    assert recues(awa, evenements.RDV_IMMINENT).count() == 1


@pytest.mark.django_db
def test_taches_faites_ou_deja_en_retard_sont_ignorees(baobab, awa):
    faite = tache(baobab, awa, "relance", hours=3)
    faite.statut = Tache.Statut.FAITE
    faite.save()
    # Une tâche déjà en retard relève de l'alerte de retard, pas du rappel.
    tache(baobab, awa, "relance", hours=-3)

    assert verifier_rappels()["relances_a_echeance"] == 0


@pytest.mark.django_db
def test_delais_parametrables(baobab, awa):
    tache(baobab, awa, "relance", hours=3)
    tache(baobab, awa, "rdv", hours=3)
    # Avec des délais de 1 heure, rien n'est encore à signaler.
    assert verifier_rappels(delai_echeance_heures=1, delai_rdv_heures=1) == {
        "relances_a_echeance": 0,
        "rdv_imminents": 0,
    }
    # Avec 4 heures, les deux le sont.
    assert verifier_rappels(delai_echeance_heures=4, delai_rdv_heures=4) == {
        "relances_a_echeance": 1,
        "rdv_imminents": 1,
    }


@pytest.mark.django_db
def test_alerte_de_retard_est_de_priorite_haute(baobab, awa):
    Tache.objects.create(
        prospect=baobab,
        responsable=awa,
        type="relance",
        echeance=timezone.now() - datetime.timedelta(hours=3),
    )
    verifier_relances()
    alerte = recues(awa, evenements.RELANCE_EN_RETARD).get()
    assert alerte.priorite == Notification.Priorite.HAUTE
