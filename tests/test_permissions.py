"""Tests du contrôle des droits : refus, cumul de rôles et matrice complète."""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from applications.comptes.matrice import ROLES, charger_matrice, droits_attendus
from applications.comptes.models import PermissionMetier, Role
from applications.comptes.permissions import a_le_droit, portees

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


def creer_utilisateur(numero, nom="Test", roles=()):
    utilisateur = Utilisateur.objects.create_user(
        email=f"u{numero}@exemple.com", password=MOT_DE_PASSE, nom=nom
    )
    for nom_role in roles:
        utilisateur.roles.add(Role.objects.get(nom=nom_role))
    return utilisateur


@pytest.mark.django_db
def test_droits_effectifs_de_chaque_role():
    charger_matrice()
    attendus = droits_attendus()
    ecarts = []
    for numero, (nom_role, _) in enumerate(ROLES):
        utilisateur = creer_utilisateur(numero, nom=nom_role, roles=[nom_role])
        for ressource, droits in attendus[nom_role].items():
            for action in PermissionMetier.Action.values:
                obtenu = portees(utilisateur, ressource, action)
                attendu = {portee for a, portee in droits if a == action}
                if obtenu != attendu:
                    ecarts.append(f"{nom_role} / {ressource} / {action}")
    assert ecarts == []


@pytest.mark.django_db
def test_utilisateur_sans_role_refuse_partout():
    charger_matrice()
    utilisateur = creer_utilisateur(1)
    assert not a_le_droit(utilisateur, "Prospects", "L")
    assert portees(utilisateur, "Contrats", "V") == set()


@pytest.mark.django_db
def test_visiteur_anonyme_refuse():
    charger_matrice()
    assert not a_le_droit(AnonymousUser(), "Prospects", "L")


@pytest.mark.django_db
def test_compte_suspendu_perd_ses_droits():
    charger_matrice()
    utilisateur = creer_utilisateur(1, roles=["Commercial"])
    assert a_le_droit(utilisateur, "Prospects", "L")
    utilisateur.statut = Utilisateur.Statut.SUSPENDU
    utilisateur.save()
    assert not a_le_droit(utilisateur, "Prospects", "L")


@pytest.mark.django_db
def test_superutilisateur_sans_role_n_a_pas_de_droit_metier():
    charger_matrice()
    admin = Utilisateur.objects.create_superuser(
        email="admin@exemple.com", password=MOT_DE_PASSE, nom="Admin"
    )
    assert not a_le_droit(admin, "Contrats", "L")


@pytest.mark.django_db
def test_droits_d_un_commercial():
    charger_matrice()
    commercial = creer_utilisateur(1, roles=["Commercial"])
    assert portees(commercial, "Prospects", "L") == {"propre"}
    assert a_le_droit(commercial, "Contrats", "C")
    assert not a_le_droit(commercial, "Prospects", "S")
    assert not a_le_droit(commercial, "Exports de données", "E")


@pytest.mark.django_db
def test_cumul_de_roles():
    charger_matrice()
    utilisateur = creer_utilisateur(1, roles=["Commercial", "Responsable data"])
    assert a_le_droit(utilisateur, "Prospects", "L")
    assert a_le_droit(utilisateur, "Fiches partenaires", "V")
    assert a_le_droit(utilisateur, "Exports de données", "E")
