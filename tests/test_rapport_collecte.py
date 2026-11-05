"""Tests du journal des rejets et des compteurs de qualité d'une collecte."""
import pytest

from applications.collecte.models import LigneRejetee, SourceDonnees
from applications.collecte.services import importer_csv, traiter_lignes


@pytest.fixture
def source(db):
    return SourceDonnees.objects.create(nom="Source de rapport", conditions_validees=True)


@pytest.mark.django_db
def test_chaque_ligne_rejetee_est_journalisee_avec_son_motif(source):
    lignes = [
        {"nom_commercial": "Atelier A", "ville": "Dakar", "telephone": "770000000"},
        {"ville": "Dakar"},  # nom manquant
        {"nom_commercial": "X" * 201},  # trop long
    ]
    collecte, erreurs = traiter_lignes(lignes, source)

    assert collecte.nb_fiches == 1 and collecte.nb_erreurs == 2 and len(erreurs) == 2
    rejets = list(collecte.rejets.all())
    # Les données commencent à la ligne 2 : la deuxième ligne de données est la ligne 3.
    assert [r.numero for r in rejets] == [3, 4]
    assert "manquant" in rejets[0].motif
    assert "dépasse" in rejets[1].motif
    assert "Dakar" in rejets[0].contenu


@pytest.mark.django_db
def test_le_contenu_journalise_est_tronque(source):
    collecte, _ = traiter_lignes([{"nom_commercial": "X" * 1000}], source)
    assert len(collecte.rejets.get().contenu) <= 500


@pytest.mark.django_db
def test_fiches_incompletes_comptees(source):
    lignes = [
        {"nom_commercial": "Complet", "ville": "Dakar", "telephone": "770000000"},
        {"nom_commercial": "Sans contact", "ville": "Dakar"},
        {"nom_commercial": "Sans ville", "telephone": "770000001"},
    ]
    collecte, _ = traiter_lignes(lignes, source)
    assert collecte.nb_fiches == 3 and collecte.nb_incomplets == 2


@pytest.mark.django_db
def test_doublons_comptes_par_collecte(source):
    lignes = [{"nom_commercial": "Atelier Doublon", "ville": "Dakar", "email": "a@b.sn"}]
    premiere, _ = traiter_lignes(lignes, source)
    seconde, _ = traiter_lignes(lignes, source)
    assert premiere.nb_doublons == 0
    assert seconde.nb_doublons == 1


@pytest.mark.django_db
def test_l_import_de_fichier_alimente_aussi_le_journal(source):
    contenu = "nom_commercial,ville\nAtelier Fichier,Dakar\n,Thiès\n".encode()
    collecte, erreurs = importer_csv(contenu, source)
    assert len(erreurs) == 1
    assert LigneRejetee.objects.filter(collecte=collecte, numero=3).exists()
