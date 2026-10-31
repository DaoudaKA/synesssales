"""Tests de la matrice des rôles et permissions (annexe G)."""
import pytest

from applications.comptes.matrice import (
    RESSOURCES,
    ROLES,
    analyser_cellule,
    charger_matrice,
    droits_attendus,
)
from applications.comptes.models import PermissionMetier, Role


def droits(nom_role, ressource):
    role = Role.objects.get(nom=nom_role)
    return {f"{p.action}:{p.portee}" for p in role.permissions.filter(ressource=ressource)}


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("CMSA", ("CMSA", "toute")),
        ("L*", ("L", "perimetre")),
        ("CML (p)", ("CML", "propre")),
        ("—", ("", "toute")),
    ],
)
def test_analyse_d_une_cellule(texte, attendu):
    assert analyser_cellule(texte) == attendu


def test_cellule_invalide_refusee():
    with pytest.raises(ValueError):
        analyser_cellule("LZ")


def test_matrice_complete():
    assert len(ROLES) == 8
    assert len(RESSOURCES) == 16
    assert all(len(cellules) == len(ROLES) for _, cellules in RESSOURCES)


@pytest.mark.django_db
def test_chargement_repetable_sans_doublon():
    charger_matrice()
    nb_permissions = PermissionMetier.objects.count()
    charger_matrice()
    assert Role.objects.count() == 8
    assert PermissionMetier.objects.count() == nb_permissions


@pytest.mark.django_db
def test_chaque_cellule_de_la_matrice():
    charger_matrice()
    ecarts = []
    for nom, par_ressource in droits_attendus().items():
        role = Role.objects.get(nom=nom)
        for ressource, attendus in par_ressource.items():
            obtenus = {(p.action, p.portee) for p in role.permissions.filter(ressource=ressource)}
            if obtenus != attendus:
                ecarts.append(f"{nom} / {ressource}")
    assert ecarts == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "ressource", "attendu"),
    [
        ("Commercial", "Prospects", {"C:propre", "M:propre", "L:propre"}),
        ("Chef d'équipe", "Prospects", {"C:perimetre", "M:perimetre", "L:perimetre"}),
        ("Lecteur autorisé", "Contrats", set()),
        (
            "Administrateur système",
            "Utilisateurs, rôles, permissions",
            {"C:toute", "M:toute", "S:toute", "A:toute"},
        ),
        (
            "Responsable data",
            "Fiches partenaires",
            {"C:toute", "M:toute", "V:toute", "S:toute", "E:toute"},
        ),
        ("Direction", "Exports de données", {"E:toute"}),
        ("Lecteur autorisé", "Journal d'audit", {"L:perimetre"}),
        ("Administrateur système", "Enregistrements vocaux", {"A:toute"}),
        ("Commercial", "Exports de données", set()),
        ("Analyste ou responsable métier", "Enregistrements vocaux", set()),
    ],
)
def test_droits_cles_recopies_a_la_main(role, ressource, attendu):
    charger_matrice()
    assert droits(role, ressource) == attendu
