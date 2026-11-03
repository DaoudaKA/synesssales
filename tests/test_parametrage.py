"""Tests du paramétrage des notifications (brique 5)."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import JournalAudit, Role
from applications.notifications import evenements
from applications.notifications.models import Notification, Parametre
from applications.notifications.parametres import PARAMETRES, valeur
from applications.notifications.relances import verifier_relances
from applications.ventes.models import Prospect, Tache

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"
ADRESSE = "/parametres-notifications/"
CLE = "SEUIL_ESCALADE_RELANCES_JOURS"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def utilisateur_avec_role(email, role):
    personne = Utilisateur.objects.create(email=email, nom=email)
    personne.roles.add(Role.objects.get(nom=role))
    return personne


@pytest.fixture
def administrateur(demo):
    return utilisateur_avec_role("admin-test@exemple.com", "Administrateur système")


@pytest.fixture
def responsable(demo):
    return utilisateur_avec_role("responsable@exemple.com", "Responsable commercial")


def donnees(**modifications):
    """Formulaire complet avec les valeurs courantes, dont certaines modifiées."""
    envoyees = {cle: valeur(cle) for cle in PARAMETRES}
    envoyees.update(modifications)
    return envoyees


@pytest.mark.django_db
def test_valeur_par_defaut_puis_valeur_enregistree(demo, administrateur):
    assert valeur(CLE) == PARAMETRES[CLE]["defaut"]
    Parametre.objects.create(cle=CLE, valeur=9, modifie_par=administrateur)
    assert valeur(CLE) == 9
    with pytest.raises(KeyError):
        valeur("CLE_INCONNUE")


@pytest.mark.django_db
def test_administrateur_modifie_un_seuil_et_c_est_journalise(client, administrateur):
    client.force_login(administrateur)
    assert client.get(ADRESSE).status_code == 200
    avant = JournalAudit.objects.count()

    reponse = client.post(ADRESSE, donnees(**{CLE: 5}))
    assert reponse.status_code == 302
    assert valeur(CLE) == 5
    assert Parametre.objects.get(cle=CLE).modifie_par == administrateur
    # Une seule valeur a changé : une seule ligne d'audit.
    assert JournalAudit.objects.count() == avant + 1


@pytest.mark.django_db
def test_responsable_commercial_peut_modifier(client, responsable):
    client.force_login(responsable)
    client.post(ADRESSE, donnees(**{CLE: 4}))
    assert valeur(CLE) == 4


@pytest.mark.django_db
def test_valeurs_identiques_ne_creent_rien(client, administrateur):
    client.force_login(administrateur)
    avant = JournalAudit.objects.count()
    client.post(ADRESSE, donnees())
    assert not Parametre.objects.exists()
    assert JournalAudit.objects.count() == avant


@pytest.mark.django_db
def test_acces_refuse_sans_le_droit(client, demo):
    direction = utilisateur_avec_role("direction@exemple.com", "Direction")
    awa = Utilisateur.objects.get(email="commercial1@exemple.com")
    chef = awa.equipe.chef_equipe
    # Visiteur anonyme : renvoi vers la connexion.
    assert client.get(ADRESSE).status_code == 302
    for personne in (awa, chef, direction):
        client.force_login(personne)
        assert client.get(ADRESSE).status_code == 403
        assert client.post(ADRESSE, donnees(**{CLE: 6})).status_code == 403
    assert not Parametre.objects.exists()


@pytest.mark.django_db
def test_valeurs_hors_bornes_sont_refusees(client, administrateur):
    client.force_login(administrateur)
    for mauvaise in (-1, PARAMETRES[CLE]["max"] + 1):
        reponse = client.post(ADRESSE, donnees(**{CLE: mauvaise}))
        assert reponse.status_code == 200  # le formulaire est réaffiché avec l'erreur
    assert not Parametre.objects.exists()


@pytest.mark.django_db
def test_seuil_enregistre_est_utilise_par_la_verification(demo):
    awa = Utilisateur.objects.get(email="commercial1@exemple.com")
    chef = awa.equipe.chef_equipe
    baobab = Prospect.objects.get(nom="Garage Baobab")
    Tache.objects.create(
        prospect=baobab,
        responsable=awa,
        type="relance",
        echeance=timezone.now() - datetime.timedelta(days=3),
    )
    # Par défaut (2 jours), un retard de 3 jours est escaladé ; avec 10 jours, non.
    Parametre.objects.create(cle=CLE, valeur=10)
    assert verifier_relances()["escalades"] == 0
    assert not Notification.objects.filter(
        destinataire=chef, type=evenements.RELANCE_ESCALADEE
    ).exists()


@pytest.mark.django_db
def test_lien_de_parametrage_selon_les_droits(client, administrateur, demo):
    awa = Utilisateur.objects.get(email="commercial1@exemple.com")
    client.force_login(administrateur)
    assert client.get("/notifications/").context["peut_parametrer_notifications"] is True
    client.force_login(awa)
    assert client.get("/notifications/").context["peut_parametrer_notifications"] is False
