"""Tests de l'envoi des notifications par e-mail (brique 5)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import Role
from applications.notifications.courriels import envoyer_courriels
from applications.notifications.models import Notification
from applications.ventes import services
from applications.ventes.models import Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def personne(db):
    return Utilisateur.objects.create(email="destinataire@exemple.com", nom="Destinataire")


def creer(destinataire, **options):
    """Une notification qui demande l'e-mail (sauf indication contraire)."""
    options.setdefault("par_courriel", True)
    return Notification.objects.create(
        destinataire=destinataire,
        type="test",
        message="Un contrat est à valider.",
        lien="/prospects/1/",
        **options,
    )


@pytest.mark.django_db
def test_envoi_du_courriel_avec_lien_absolu(personne, mailoutbox, settings):
    settings.SITE_URL = "http://exemple.test"
    notification = creer(personne)
    bilan = envoyer_courriels()

    assert bilan == {"envoyes": 1, "echecs": 0, "restants": 0}
    assert len(mailoutbox) == 1
    courriel = mailoutbox[0]
    assert courriel.to == ["destinataire@exemple.com"]
    assert courriel.subject.startswith("[SYNESS Sales]")
    assert "http://exemple.test/prospects/1/" in courriel.body
    notification.refresh_from_db()
    assert notification.courriel_envoye_le is not None

    # Un second passage n'envoie rien de plus.
    envoyer_courriels()
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_notification_sans_demande_d_e_mail_n_est_pas_envoyee(personne, mailoutbox):
    creer(personne, par_courriel=False)
    assert envoyer_courriels()["envoyes"] == 0
    assert mailoutbox == []


@pytest.mark.django_db
def test_compte_suspendu_ne_recoit_rien(personne, mailoutbox):
    personne.statut = "suspendu"
    personne.save()
    creer(personne)
    assert envoyer_courriels()["envoyes"] == 0
    assert mailoutbox == []


@pytest.mark.django_db
def test_echec_puis_nouvelles_tentatives_limitees(personne, monkeypatch):
    def panne(*args, **kwargs):
        raise OSError("serveur indisponible")

    monkeypatch.setattr("applications.notifications.courriels.send_mail", panne)
    notification = creer(personne)

    for _ in range(3):
        assert envoyer_courriels()["echecs"] == 1
    notification.refresh_from_db()
    assert notification.courriel_tentatives == 3
    assert "serveur indisponible" in notification.courriel_erreur
    # Après 3 tentatives, on n'insiste plus.
    assert envoyer_courriels() == {"envoyes": 0, "echecs": 0, "restants": 0}


@pytest.mark.django_db
def test_reprise_apres_une_panne(personne, monkeypatch, mailoutbox):
    def panne(*args, **kwargs):
        raise OSError("serveur indisponible")

    monkeypatch.setattr("applications.notifications.courriels.send_mail", panne)
    creer(personne)
    envoyer_courriels()
    monkeypatch.undo()  # le serveur revient

    assert envoyer_courriels()["envoyes"] == 1
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_plafond_par_execution(personne, mailoutbox):
    for _ in range(3):
        creer(personne)
    premier = envoyer_courriels(plafond=2)
    assert premier["envoyes"] == 2 and premier["restants"] == 1
    assert envoyer_courriels(plafond=2)["envoyes"] == 1
    assert len(mailoutbox) == 3


@pytest.mark.django_db
def test_contrat_soumis_part_par_e_mail_mais_pas_la_decision(db, mailoutbox):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)
    baobab = Prospect.objects.get(nom="Garage Baobab")
    responsable = Utilisateur.objects.create(
        email="responsable@exemple.com", nom="Responsable Test"
    )
    responsable.roles.add(Role.objects.get(nom="Responsable commercial"))

    contrat = services.soumettre_contrat(baobab, timezone.localdate())
    alerte = Notification.objects.get(destinataire=responsable, type="contrat_a_valider")
    assert alerte.par_courriel is True

    envoyer_courriels()
    assert [m.to for m in mailoutbox] == [["responsable@exemple.com"]]

    # La décision prévient le commercial dans l'application seulement.
    services.valider_contrat(contrat, responsable)
    decision = Notification.objects.get(type="contrat_valide")
    assert decision.par_courriel is False


@pytest.mark.django_db
def test_commande_affiche_un_compte_rendu(personne, mailoutbox):
    from io import StringIO

    creer(personne)
    sortie = StringIO()
    call_command("envoyer_courriels", stdout=sortie)
    assert "1 e-mail(s) envoyé(s)" in sortie.getvalue()
