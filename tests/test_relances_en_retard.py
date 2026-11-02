"""Tests des relances en retard et de l'escalade au chef d'équipe (brique 3)."""
import datetime
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.notifications import evenements
from applications.notifications.models import Notification
from applications.notifications.relances import verifier_relances
from applications.ventes.models import Prospect, Tache

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def baobab(demo):
    """Prospect de démonstration suivi par commercial1 (équipe Dakar)."""
    return Prospect.objects.get(nom="Garage Baobab")


@pytest.fixture
def awa(demo):
    return Utilisateur.objects.get(email="commercial1@exemple.com")


@pytest.fixture
def chef(awa):
    """Chef de l'équipe d'Awa."""
    return awa.equipe.chef_equipe


def il_y_a(**duree):
    return timezone.now() - datetime.timedelta(**duree)


def tache(baobab, responsable, **duree):
    """Une relance à faire dont l'échéance est passée depuis la durée donnée."""
    return Tache.objects.create(
        prospect=baobab, responsable=responsable, type="relance", echeance=il_y_a(**duree)
    )


def recues(utilisateur, type_):
    return Notification.objects.filter(destinataire=utilisateur, type=type_)


@pytest.mark.django_db
def test_retard_recent_alerte_le_commercial_sans_escalade(baobab, awa, chef):
    tache(baobab, awa, hours=3)
    bilan = verifier_relances()

    assert bilan["en_retard"] == 1 and bilan["alertes"] == 1 and bilan["escalades"] == 0
    alerte = recues(awa, evenements.RELANCE_EN_RETARD).get()
    assert alerte.lien == f"/prospects/{baobab.pk}/"
    assert not recues(chef, evenements.RELANCE_ESCALADEE).exists()


@pytest.mark.django_db
def test_retard_au_dela_du_seuil_escalade_au_chef(baobab, awa, chef):
    tache(baobab, awa, days=3)
    bilan = verifier_relances()

    assert bilan["escalades"] == 1
    escalade = recues(chef, evenements.RELANCE_ESCALADEE).get()
    assert escalade.priorite == Notification.Priorite.HAUTE
    assert "Garage Baobab" in escalade.message


@pytest.mark.django_db
def test_relancer_la_verification_ne_cree_pas_de_doublon(baobab, awa, chef):
    tache(baobab, awa, days=3)
    verifier_relances()
    second = verifier_relances()

    # La tâche est toujours en retard, mais aucune nouvelle alerte n'est créée.
    assert second["en_retard"] == 1
    assert second["alertes"] == 0 and second["escalades"] == 0
    assert recues(awa, evenements.RELANCE_EN_RETARD).count() == 1
    assert recues(chef, evenements.RELANCE_ESCALADEE).count() == 1


@pytest.mark.django_db
def test_taches_futures_faites_ou_annulees_sont_ignorees(baobab, awa):
    Tache.objects.create(
        prospect=baobab,
        responsable=awa,
        type="relance",
        echeance=timezone.now() + datetime.timedelta(days=1),
    )
    faite = tache(baobab, awa, days=5)
    faite.statut = Tache.Statut.FAITE
    faite.save()
    annulee = tache(baobab, awa, days=5)
    annulee.statut = Tache.Statut.ANNULEE
    annulee.save()

    assert verifier_relances()["en_retard"] == 0
    assert not Notification.objects.filter(type=evenements.RELANCE_EN_RETARD).exists()


@pytest.mark.django_db
def test_seuil_parametrable(baobab, awa, chef):
    tache(baobab, awa, hours=3)
    # Avec un seuil de 0 jour, même un retard de quelques heures est escaladé.
    assert verifier_relances(seuil_jours=0)["escalades"] == 1


@pytest.mark.django_db
def test_commercial_sans_equipe_est_signale_sans_escalade(baobab, awa):
    tache(baobab, awa, days=3)
    awa.equipe = None
    awa.save()
    bilan = verifier_relances()

    assert bilan["sans_chef"] == 1 and bilan["escalades"] == 0
    # Le commercial reçoit tout de même son alerte.
    assert recues(awa, evenements.RELANCE_EN_RETARD).count() == 1


@pytest.mark.django_db
def test_un_chef_en_retard_n_est_pas_escalade_a_lui_meme(baobab, chef):
    tache(baobab, chef, days=5)
    bilan = verifier_relances()

    assert recues(chef, evenements.RELANCE_EN_RETARD).count() == 1
    assert bilan["escalades"] == 0 and bilan["sans_chef"] == 0
    assert not recues(chef, evenements.RELANCE_ESCALADEE).exists()


@pytest.mark.django_db
def test_commande_affiche_un_compte_rendu(baobab, awa):
    tache(baobab, awa, days=3)
    sortie = StringIO()
    call_command("verifier_relances", stdout=sortie)
    assert "1 tâche(s) en retard" in sortie.getvalue()
    assert "1 escalade(s)" in sortie.getvalue()
