"""Tests de l'alerte « objectif en écart » (brique 5)."""
import datetime
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import Role
from applications.notifications import evenements
from applications.notifications.models import Notification
from applications.notifications.objectifs import verifier_objectifs
from applications.ventes.models import Contrat, Objectif, Prospect

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
def responsable(demo):
    personne = Utilisateur.objects.create(email="responsable@exemple.com", nom="Responsable Test")
    personne.roles.add(Role.objects.get(nom="Responsable commercial"))
    return personne


def jour(decalage=0):
    return timezone.localdate() + datetime.timedelta(days=decalage)


@pytest.fixture
def objectif(baobab, awa, responsable):
    """Objectif collectif de l'équipe Dakar : 4 contrats, période de 29 jours dont 15 écoulés."""
    return Objectif.objects.create(
        produit=baobab.produit,
        equipe=awa.equipe,
        cible=4,
        date_debut=jour(-14),
        date_fin=jour(14),
        cree_par=responsable,
    )


def alertes(destinataire):
    return Notification.objects.filter(
        destinataire=destinataire, type=evenements.OBJECTIF_EN_ECART
    )


@pytest.mark.django_db
def test_objectif_en_retard_alerte_les_responsables_seulement(
    objectif, responsable, awa
):
    bilan = verifier_objectifs()

    assert bilan["en_ecart"] == 1 and bilan["alertes"] == 1
    alerte = alertes(responsable).get()
    assert alerte.lien == "/objectifs/"
    assert alerte.par_courriel is True  # la matrice prévoit application + e-mail
    # Le commercial et le chef d'équipe ne reçoivent pas cette alerte.
    chef = awa.equipe.chef_equipe
    assert not alertes(awa).exists() and not alertes(chef).exists()


@pytest.mark.django_db
def test_administrateur_systeme_n_est_pas_destinataire(objectif):
    admin = Utilisateur.objects.create(email="admin-test@exemple.com", nom="Admin")
    admin.roles.add(Role.objects.get(nom="Administrateur système"))
    verifier_objectifs()
    assert not alertes(admin).exists()


@pytest.mark.django_db
def test_objectif_dans_les_temps_n_alerte_pas(objectif, baobab, responsable):
    # 1 contrat validé sur 4 : 25 % d'atteinte, mais seulement la tolérance de 20 points
    # est à rattraper si l'attendu est de 52 % : on prend ici un objectif plus facile.
    objectif.cible = 1
    objectif.save()
    Contrat.objects.create(
        prospect=baobab,
        date_signature=jour(-1),
        statut_validation=Contrat.StatutValidation.VALIDE,
    )
    assert verifier_objectifs()["en_ecart"] == 0
    assert not alertes(responsable).exists()


@pytest.mark.django_db
def test_objectifs_a_venir_ou_termines_sont_ignores(baobab, awa, responsable):
    for debut, fin in ((jour(1), jour(10)), (jour(-20), jour(-5))):
        Objectif.objects.create(
            produit=baobab.produit,
            equipe=awa.equipe,
            cible=4,
            date_debut=debut,
            date_fin=fin,
            cree_par=responsable,
        )
    assert verifier_objectifs()["objectifs_suivis"] == 0


@pytest.mark.django_db
def test_une_alerte_par_semaine(objectif, responsable):
    verifier_objectifs()
    verifier_objectifs()
    assert alertes(responsable).count() == 1
    # Une semaine plus tard, l'objectif est toujours en retard : nouvelle alerte.
    verifier_objectifs(aujourdhui=jour(7))
    assert alertes(responsable).count() == 2


@pytest.mark.django_db
def test_tolerance_parametrable(objectif, responsable):
    # Attendu : 52 %, atteint : 0 %. Une tolérance de 60 points laisse passer.
    assert verifier_objectifs(tolerance=60)["en_ecart"] == 0
    assert verifier_objectifs(tolerance=10)["en_ecart"] == 1


@pytest.mark.django_db
def test_commande_affiche_un_compte_rendu(objectif, responsable):
    sortie = StringIO()
    call_command("verifier_objectifs", stdout=sortie)
    assert "1 objectif(s) en cours" in sortie.getvalue()
    assert "1 alerte(s) créée(s)" in sortie.getvalue()
