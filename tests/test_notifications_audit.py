"""Tests des notifications et du journal d'audit."""
import pytest
from django.contrib.auth import get_user_model

from applications.comptes.models import JournalAudit
from applications.notifications.models import Notification

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def utilisateur(db):
    return Utilisateur.objects.create_user(
        email="com@exemple.com", password=MOT_DE_PASSE, nom="Commercial"
    )


@pytest.mark.django_db
def test_notification_par_defaut(utilisateur):
    notification = Notification.objects.create(
        destinataire=utilisateur, type="relance_a_echeance"
    )
    assert notification.lue is False
    assert notification.priorite == Notification.Priorite.MOYENNE
    assert notification.canal == Notification.Canal.APPLICATION
    assert notification in utilisateur.notifications.all()


@pytest.mark.django_db
def test_notification_supprimee_avec_le_destinataire(utilisateur):
    Notification.objects.create(destinataire=utilisateur, type="contrat_a_valider")
    utilisateur.delete()
    assert Notification.objects.count() == 0


@pytest.mark.django_db
def test_entree_d_audit_enregistree(utilisateur):
    entree = JournalAudit.objects.create(
        utilisateur=utilisateur,
        action="export",
        ressource="Partenaires",
        detail="Export de 120 fiches",
    )
    assert entree in utilisateur.actions_journalisees.all()
    assert entree.date is not None


@pytest.mark.django_db
def test_entree_d_audit_non_modifiable(utilisateur):
    entree = JournalAudit.objects.create(utilisateur=utilisateur, action="export", ressource="X")
    entree.action = "autre"
    with pytest.raises(PermissionError):
        entree.save()


@pytest.mark.django_db
def test_entree_d_audit_non_supprimable(utilisateur):
    entree = JournalAudit.objects.create(utilisateur=utilisateur, action="export", ressource="X")
    with pytest.raises(PermissionError):
        entree.delete()


@pytest.mark.django_db
def test_entree_d_audit_conservee_apres_suppression_de_l_utilisateur(utilisateur):
    entree = JournalAudit.objects.create(utilisateur=utilisateur, action="export", ressource="X")
    utilisateur.delete()
    entree.refresh_from_db()
    assert entree.utilisateur is None
