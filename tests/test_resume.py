"""Tests du résumé périodique (brique 5)."""
import datetime
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.comptes.models import Role
from applications.notifications import evenements
from applications.notifications.courriels import envoyer_courriels
from applications.notifications.models import Notification
from applications.notifications.resume import envoyer_resumes
from applications.ventes.models import Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def utilisateur_avec_role(email, role):
    personne = Utilisateur.objects.create(email=email, nom=email)
    personne.roles.add(Role.objects.get(nom=role))
    return personne


@pytest.fixture
def direction(demo):
    return utilisateur_avec_role("direction@exemple.com", "Direction")


@pytest.fixture
def responsable(demo):
    return utilisateur_avec_role("responsable@exemple.com", "Responsable commercial")


def resumes(destinataire):
    return Notification.objects.filter(
        destinataire=destinataire, type=evenements.RESUME_PERIODIQUE
    )


@pytest.mark.django_db
def test_seuls_direction_et_responsables_recoivent_le_resume(direction, responsable):
    admin = utilisateur_avec_role("admin-test@exemple.com", "Administrateur système")
    awa = Utilisateur.objects.get(email="commercial1@exemple.com")
    chef = awa.equipe.chef_equipe
    envoyer_resumes()

    assert resumes(direction).count() == 1 and resumes(responsable).count() == 1
    # Commercial (propre), chef d'équipe (périmètre) et administrateur (aucun accès).
    for exclu in (awa, chef, admin):
        assert not resumes(exclu).exists()


@pytest.mark.django_db
def test_contenu_du_resume(responsable):
    total = Prospect.objects.count()
    envoyer_resumes()

    resume = resumes(responsable).get()
    assert resume.priorite == Notification.Priorite.BASSE
    assert resume.par_courriel is True  # la matrice prévoit l'e-mail
    assert resume.lien == "/tableau-de-bord/"
    # Les prospects de démonstration viennent d'être créés : tous sont « nouveaux ».
    assert f"{total} prospect(s) dont {total} nouveau(x)" in resume.message
    # Le responsable commercial a le droit de valider : le compteur est présent.
    assert "contrat(s) à valider" in resume.message


@pytest.mark.django_db
def test_le_resume_de_la_direction_n_affiche_pas_les_contrats_a_valider(direction):
    envoyer_resumes()
    assert "contrat(s) à valider" not in resumes(direction).get().message


@pytest.mark.django_db
def test_un_seul_resume_par_semaine(responsable):
    envoyer_resumes()
    envoyer_resumes()
    assert resumes(responsable).count() == 1
    # La semaine suivante, un nouveau résumé est créé.
    suivante = datetime.date.today() + datetime.timedelta(days=7)
    envoyer_resumes(aujourdhui=suivante)
    assert resumes(responsable).count() == 2


@pytest.mark.django_db
def test_le_resume_part_par_e_mail(responsable, mailoutbox):
    envoyer_resumes()
    envoyer_courriels()
    destinataires = [m.to[0] for m in mailoutbox]
    assert "responsable@exemple.com" in destinataires
    courriel = next(m for m in mailoutbox if m.to == ["responsable@exemple.com"])
    assert "Résumé de la semaine" in courriel.subject


@pytest.mark.django_db
def test_commande_affiche_un_compte_rendu(responsable):
    sortie = StringIO()
    call_command("envoyer_resume", stdout=sortie)
    assert "résumé(s) créé(s)" in sortie.getvalue()
