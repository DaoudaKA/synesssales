"""Tests des connecteurs : garde d'autorisation, pipeline commun, échecs enregistrés."""
import time
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from applications.collecte.connecteurs import (
    CONNECTEURS,
    BaseConnecteur,
    lancer_collecte,
)
from applications.collecte.models import AlerteDoublon, Collecte, Provenance, SourceDonnees
from applications.collecte.services import (
    MAX_LIGNES,
    ImportInvalide,
    SourceNonAutorisee,
    valider_source,
)
from applications.partenaires.models import Partenaire

Utilisateur = get_user_model()


@pytest.fixture
def responsable_data(db):
    # Même méthode que test_sources.py : la démo crée les rôles et les comptes.
    call_command("charger_demo", "--mot-de-passe", "daouda")
    return Utilisateur.objects.get(email="data@exemple.com")


@pytest.fixture
def source(db):
    return SourceDonnees.objects.create(nom="Source fictive", code_connecteur="demonstration")


@pytest.fixture
def source_autorisee(source, responsable_data):
    valider_source(source, responsable_data, "Courriel de SYNESS (test)")
    return source


@pytest.mark.django_db
def test_source_non_autorisee_refusee_sans_rien_creer(source):
    with pytest.raises(SourceNonAutorisee):
        lancer_collecte(source)
    assert not Collecte.objects.exists() and not Partenaire.objects.exists()


@pytest.mark.django_db
def test_collecte_d_une_source_autorisee_cree_les_fiches_avec_provenance(source_autorisee):
    collecte, erreurs = lancer_collecte(source_autorisee)

    assert erreurs == []
    assert collecte.statut == Collecte.Statut.TERMINEE
    assert collecte.nb_fiches == 3 and collecte.version_connecteur == "1.0"
    assert Partenaire.objects.filter(nom_commercial="Atelier Fictif Un").exists()
    # Chaque fiche garde sa source et la date de la collecte.
    provenance = Provenance.objects.filter(collecte=collecte, champ="nom_commercial")
    assert provenance.count() == 3
    assert {p.source for p in provenance} == {source_autorisee}
    assert all(p.date_collecte == collecte.date_debut for p in provenance)


@pytest.mark.django_db
def test_meme_pipeline_que_l_import_les_doublons_sont_detectes(source_autorisee):
    lancer_collecte(source_autorisee)
    assert AlerteDoublon.objects.count() == 0
    lancer_collecte(source_autorisee)  # mêmes noms, mêmes villes : 3 doublons potentiels
    assert AlerteDoublon.objects.count() == 3


@pytest.mark.django_db
def test_source_sans_connecteur_ou_connecteur_inconnu(source_autorisee):
    for code in ("", "inexistant"):
        source_autorisee.code_connecteur = code
        source_autorisee.save()
        with pytest.raises(ImportInvalide):
            lancer_collecte(source_autorisee)


class EnPanne(BaseConnecteur):
    code_source = "en-panne"
    version = "2.0"

    def recuperer(self):
        raise ConnectionError("serveur de la source injoignable")


@pytest.mark.django_db
def test_un_echec_est_enregistre_sans_faire_planter(source_autorisee, monkeypatch):
    monkeypatch.setitem(CONNECTEURS, "en-panne", EnPanne)
    source_autorisee.code_connecteur = "en-panne"
    source_autorisee.save()

    avant = Partenaire.objects.count()  # la démo crée déjà des partenaires
    collecte, erreurs = lancer_collecte(source_autorisee)
    assert collecte.statut == Collecte.Statut.EN_ERREUR
    assert "injoignable" in collecte.message_erreur
    assert collecte.version_connecteur == "2.0"
    assert collecte.nb_fiches == 0 and erreurs
    assert Partenaire.objects.count() == avant  # aucune fiche créée


class LignesMelangees(BaseConnecteur):
    code_source = "melange"
    delai_secondes = 0

    def recuperer(self):
        return None

    def analyser(self, brut):
        return [{"nom_commercial": "Atelier Valide", "ville": "Dakar"}, {"ville": "Dakar"}]


@pytest.mark.django_db
def test_lignes_invalides_sont_comptees_sans_bloquer_les_autres(source_autorisee, monkeypatch):
    monkeypatch.setitem(CONNECTEURS, "melange", LignesMelangees)
    source_autorisee.code_connecteur = "melange"
    source_autorisee.save()

    collecte, erreurs = lancer_collecte(source_autorisee)
    assert collecte.statut == Collecte.Statut.TERMINEE
    assert collecte.nb_fiches == 1 and collecte.nb_erreurs == 1 and len(erreurs) == 1


class TropDeLignes(BaseConnecteur):
    code_source = "trop"
    delai_secondes = 0

    def recuperer(self):
        return None

    def analyser(self, brut):
        return [{"nom_commercial": f"Fiche {i}"} for i in range(MAX_LIGNES + 1)]


@pytest.mark.django_db
def test_volume_excessif_est_refuse(source_autorisee, monkeypatch):
    monkeypatch.setitem(CONNECTEURS, "trop", TropDeLignes)
    source_autorisee.code_connecteur = "trop"
    source_autorisee.save()

    avant = Partenaire.objects.count()  # la démo crée déjà des partenaires
    collecte, _ = lancer_collecte(source_autorisee)
    assert collecte.statut == Collecte.Statut.EN_ERREUR
    assert Partenaire.objects.count() == avant  # aucune fiche créée


class Lent(BaseConnecteur):
    code_source = "lent"
    delai_secondes = 0.5


def test_delai_minimal_entre_deux_requetes(monkeypatch):
    pauses = []
    monkeypatch.setattr(time, "sleep", pauses.append)
    monkeypatch.setattr(time, "monotonic", lambda: 100.0)
    connecteur = Lent()
    connecteur.espacer()  # première requête : pas d'attente
    connecteur.espacer()  # seconde, au même instant : attente du délai complet
    assert pauses == [0.5]


@pytest.mark.django_db
def test_commande_lancer_collecte(source_autorisee):
    sortie = StringIO()
    call_command("lancer_collecte", "Source fictive", stdout=sortie)
    assert "3 fiche(s)" in sortie.getvalue()


@pytest.mark.django_db
def test_commande_refuse_une_source_non_autorisee_ou_inconnue(source):
    with pytest.raises(CommandError):
        call_command("lancer_collecte", "Source fictive")
    with pytest.raises(CommandError):
        call_command("lancer_collecte", "Source qui n'existe pas")
    assert not Collecte.objects.exists()


@pytest.mark.django_db
def test_formulaire_n_accepte_que_les_connecteurs_du_registre(client, responsable_data):
    client.force_login(responsable_data)
    ok = client.post(
        "/sources/nouvelle/",
        {"nom": "Via connecteur", "type": "", "url": "", "code_connecteur": "demonstration"},
    )
    assert ok.status_code == 302
    assert SourceDonnees.objects.get(nom="Via connecteur").code_connecteur == "demonstration"

    refus = client.post(
        "/sources/nouvelle/",
        {"nom": "Code inventé", "type": "", "url": "", "code_connecteur": "pirate"},
    )
    assert refus.status_code == 200  # formulaire réaffiché avec l'erreur
    assert not SourceDonnees.objects.filter(nom="Code inventé").exists()
