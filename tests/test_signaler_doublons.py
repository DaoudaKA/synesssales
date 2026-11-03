"""Tests du signalement regroupé des doublons de fiches partenaires (brique 5)."""
import datetime
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.collecte.models import AlerteDoublon
from applications.notifications import evenements
from applications.notifications.doublons import signaler_doublons
from applications.notifications.models import Notification
from applications.partenaires.models import Localisation, Partenaire
from applications.partenaires.services import detecter_doublons, rejeter

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def data(demo):
    return Utilisateur.objects.get(email="data@exemple.com")


def creer(nom, ville=""):
    fiche = Partenaire.objects.create(nom_commercial=nom)
    Localisation.objects.create(partenaire=fiche, pays="Sénégal", ville=ville)
    return fiche


def creer_doublon(nom):
    """Deux fiches au même nom dans la même ville : la détection crée une alerte."""
    creer(nom, "Dakar")
    return detecter_doublons(creer(nom, "Dakar"))[0]


def recues(destinataire):
    return Notification.objects.filter(
        destinataire=destinataire, type=evenements.DOUBLONS_A_TRAITER
    )


@pytest.mark.django_db
def test_aucun_message_sans_doublon_ouvert(data):
    bilan = signaler_doublons()
    assert bilan == {"ouvertes": 0, "alertes": 0}
    assert not recues(data).exists()


@pytest.mark.django_db
def test_un_message_regroupe_pour_le_responsable_data(data):
    creer_doublon("Atelier Soleil")
    creer_doublon("Maison Lumiere")
    bilan = signaler_doublons()

    assert bilan["ouvertes"] == 2 and bilan["alertes"] == 1
    # Un seul message pour les deux doublons, pas un par doublon.
    message = recues(data).get()
    assert "2 doublon(s)" in message.message
    assert message.priorite == Notification.Priorite.BASSE
    assert message.lien == "/partenaires/doublons/"


@pytest.mark.django_db
def test_seul_le_responsable_data_est_prevenu(data):
    creer_doublon("Atelier Soleil")
    signaler_doublons()
    awa = Utilisateur.objects.get(email="commercial1@exemple.com")
    chef = awa.equipe.chef_equipe
    for autre in (awa, chef):
        assert not recues(autre).exists()


@pytest.mark.django_db
def test_pas_de_repetition_tant_que_rien_ne_change(data):
    creer_doublon("Atelier Soleil")
    signaler_doublons()
    assert signaler_doublons()["alertes"] == 0
    assert recues(data).count() == 1


@pytest.mark.django_db
def test_nouveau_message_si_le_nombre_change_ou_apres_une_semaine(data):
    creer_doublon("Atelier Soleil")
    signaler_doublons()
    # Un deuxième doublon apparaît : le nombre change, nouveau message.
    creer_doublon("Maison Lumiere")
    assert signaler_doublons()["alertes"] == 1
    assert recues(data).count() == 2
    # Une semaine plus tard, à nombre égal : un rappel.
    semaine_suivante = timezone.localdate() + datetime.timedelta(days=7)
    assert signaler_doublons(aujourdhui=semaine_suivante)["alertes"] == 1
    assert recues(data).count() == 3


@pytest.mark.django_db
def test_doublon_traite_ne_compte_plus(data):
    alerte = creer_doublon("Atelier Soleil")
    rejeter(alerte)
    assert AlerteDoublon.objects.filter(statut=AlerteDoublon.Statut.OUVERTE).count() == 0
    assert signaler_doublons() == {"ouvertes": 0, "alertes": 0}
    assert not recues(data).exists()


@pytest.mark.django_db
def test_commande_affiche_un_compte_rendu(data):
    creer_doublon("Atelier Soleil")
    sortie = StringIO()
    call_command("signaler_doublons", stdout=sortie)
    assert "1 doublon(s) en attente" in sortie.getvalue()
    assert "1 message(s) créé(s)" in sortie.getvalue()
