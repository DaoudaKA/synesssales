"""Tests des notifications déclenchées par les événements métier (brique 2)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import Role
from applications.notifications import evenements
from applications.notifications.models import Notification
from applications.ventes import services
from applications.ventes.models import Produit, Prospect

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
def responsable(demo):
    """Un Responsable commercial (droit « LV » sur les contrats)."""
    utilisateur = Utilisateur.objects.create(
        email="responsable@exemple.com", nom="Responsable Test"
    )
    utilisateur.roles.add(Role.objects.get(nom="Responsable commercial"))
    return utilisateur


def compte(email):
    return Utilisateur.objects.get(email=email)


def recues(utilisateur, type_):
    """Notifications d'un type donné reçues par une personne."""
    return Notification.objects.filter(destinataire=utilisateur, type=type_)


@pytest.mark.django_db
def test_reaffectation_previent_le_nouveau_et_l_ancien(baobab):
    awa = compte("commercial1@exemple.com")
    moussa = compte("commercial2@exemple.com")
    chef = baobab.equipe.chef_equipe
    services.reaffecter_prospect(baobab, moussa, chef, motif="Équilibrage")

    nouvelle = recues(moussa, evenements.PROSPECT_AFFECTE).get()
    assert nouvelle.lien == f"/prospects/{baobab.pk}/"
    assert "Équilibrage" in nouvelle.message
    # L'ancien est prévenu, sans lien (il n'a peut-être plus accès à la fiche).
    ancienne = recues(awa, evenements.PROSPECT_RETIRE).get()
    assert ancienne.lien == ""
    # L'auteur de l'action n'est pas notifié de sa propre action.
    assert Notification.objects.filter(destinataire=chef).count() == 0


@pytest.mark.django_db
def test_reaffectation_vers_soi_meme_ne_notifie_pas_l_auteur(baobab):
    moussa = compte("commercial2@exemple.com")
    services.reaffecter_prospect(baobab, moussa, auteur=moussa)
    assert not recues(moussa, evenements.PROSPECT_AFFECTE).exists()


@pytest.mark.django_db
def test_affectation_a_un_produit_previent_la_personne(demo):
    awa = compte("commercial1@exemple.com")
    produit = Produit.objects.first()
    # Le chargement de la démo a déjà créé des affectations (donc des notifications).
    avant = recues(awa, evenements.AFFECTATION_PRODUIT).count()
    services.affecter(awa, produit, timezone.localdate())
    apres = recues(awa, evenements.AFFECTATION_PRODUIT)
    assert apres.count() == avant + 1
    # La plus récente est celle que l'on vient de provoquer.
    assert str(produit) in apres.latest("date").message


@pytest.mark.django_db
def test_contrat_soumis_previent_les_validateurs_pas_le_commercial(baobab, responsable):
    services.soumettre_contrat(baobab, timezone.localdate())

    alerte = recues(responsable, evenements.CONTRAT_A_VALIDER).get()
    assert alerte.priorite == Notification.Priorite.HAUTE
    assert alerte.lien == "/contrats/a-valider/"
    # Le commercial propriétaire du prospect ne reçoit pas l'alerte de validation.
    awa = compte("commercial1@exemple.com")
    assert not recues(awa, evenements.CONTRAT_A_VALIDER).exists()


@pytest.mark.django_db
def test_alerte_de_validation_sans_doublon(baobab, responsable):
    contrat = services.soumettre_contrat(baobab, timezone.localdate())
    # Rejouer l'événement ne crée pas une seconde alerte (clé de regroupement).
    evenements.contrat_soumis(contrat)
    assert recues(responsable, evenements.CONTRAT_A_VALIDER).count() == 1


@pytest.mark.django_db
def test_validation_previent_le_commercial(baobab, responsable):
    contrat = services.soumettre_contrat(baobab, timezone.localdate())
    services.valider_contrat(contrat, responsable)

    awa = compte("commercial1@exemple.com")
    notification = recues(awa, evenements.CONTRAT_VALIDE).get()
    assert notification.lien == f"/prospects/{baobab.pk}/"


@pytest.mark.django_db
def test_refus_previent_le_commercial_avec_le_motif(baobab, responsable):
    contrat = services.soumettre_contrat(baobab, timezone.localdate())
    services.refuser_contrat(contrat, responsable, "Pièces manquantes")

    awa = compte("commercial1@exemple.com")
    notification = recues(awa, evenements.CONTRAT_REFUSE).get()
    assert "Pièces manquantes" in notification.message
    assert notification.priorite == Notification.Priorite.HAUTE
