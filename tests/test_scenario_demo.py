"""Tests de la commande qui charge le scénario de démonstration."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.ventes.models import Contrat, Objectif, Prospect, Tache

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


def charger():
    call_command("charger_scenario", "--mot-de-passe", MOT_DE_PASSE)


@pytest.mark.django_db
def test_scenario_cree_les_donnees_attendues():
    charger()
    responsable = Utilisateur.objects.get(email="responsable@exemple.com")
    assert responsable.roles.filter(nom="Responsable commercial").exists()
    assert Contrat.objects.filter(statut_validation=Contrat.StatutValidation.SOUMIS).count() == 2
    assert Contrat.objects.filter(statut_validation=Contrat.StatutValidation.VALIDE).count() == 1
    refuse = Contrat.objects.get(statut_validation=Contrat.StatutValidation.REFUSE)
    assert refuse.motif_refus
    assert Objectif.objects.count() == 3
    # Une seule relance en retard : celle qui sert à montrer l'alerte.
    en_retard = Tache.objects.filter(statut="a_faire", echeance__lt=timezone.now())
    assert en_retard.count() == 1
    # Le contrat validé a fait passer son prospect à « Gagné ».
    assert Prospect.objects.get(nom="Mécanique Lac Rose").statut == Prospect.Statut.GAGNE


@pytest.mark.django_db
def test_scenario_relancable_sans_doublons():
    charger()
    avant = (Contrat.objects.count(), Objectif.objects.count(), Tache.objects.count())
    charger()
    assert (Contrat.objects.count(), Objectif.objects.count(), Tache.objects.count()) == avant
    assert Prospect.objects.filter(nom="Teranga Auto Thiès").count() == 1


@pytest.mark.django_db
def test_scenario_montre_le_contact_multiple_et_les_taux(client):
    charger()
    baobab = Prospect.objects.get(nom="Garage Baobab")
    client.force_login(Utilisateur.objects.get(email="commercial1@exemple.com"))
    contenu = client.get(f"/prospects/{baobab.pk}/").content.decode()
    assert "Contact multiple possible" in contenu
    client.force_login(Utilisateur.objects.get(email="responsable@exemple.com"))
    contenu = client.get("/objectifs/").content.decode()
    assert "50 %" in contenu  # Moussa : 1 contrat sur 2
    assert "25 %" in contenu  # Équipe Dakar : 1 contrat sur 4
