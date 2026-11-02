"""Tests de l'avertissement de contact multiple sur la fiche prospect."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.partenaires.models import Partenaire
from applications.ventes.models import Prospect
from applications.ventes.services import contacts_en_double

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def baobab(demo):
    """Prospect de démonstration suivi par commercial1 (équipe Dakar)."""
    return Prospect.objects.get(nom="Garage Baobab")


def compte(email):
    return Utilisateur.objects.get(email=email)


def autre_prospect(baobab, nom, **champs):
    """Crée un prospect suivi par commercial3 (équipe Thiès) sur le même produit."""
    voisin = compte("commercial3@exemple.com")
    valeurs = {"produit": baobab.produit, "commercial": voisin, "equipe": voisin.equipe}
    valeurs.update(champs)
    return Prospect.objects.create(nom=nom, **valeurs)


def ouvrir_fiche(client, prospect, email="commercial1@exemple.com"):
    client.force_login(compte(email))
    reponse = client.get(f"/prospects/{prospect.pk}/")
    assert reponse.status_code == 200
    return reponse.content.decode()


@pytest.mark.django_db
def test_meme_partenaire_declenche_l_avertissement(client, baobab):
    teranga = Partenaire.objects.get(nom_commercial="Garage Teranga")
    baobab.partenaire = teranga
    baobab.save()
    autre_prospect(baobab, "Contact Sarl", partenaire=teranga)
    contenu = ouvrir_fiche(client, baobab)
    assert "Contact multiple possible" in contenu
    assert "même partenaire" in contenu
    assert compte("commercial3@exemple.com").nom in contenu


@pytest.mark.django_db
def test_nom_tres_proche_declenche_l_avertissement(client, baobab):
    autre_prospect(baobab, "Garage Baobab")  # même nom, autre commercial
    contenu = ouvrir_fiche(client, baobab)
    assert "nom très proche" in contenu


@pytest.mark.django_db
def test_nom_sans_accent_est_reconnu(demo):
    fiche = Prospect.objects.get(nom="Garage Baobab")
    fiche.nom = "Garage Baobàb"
    fiche.save()
    autre_prospect(fiche, "GARAGE BAOBAB")
    assert [motif for _, motif in contacts_en_double(fiche)] == ["nom très proche"]


@pytest.mark.django_db
def test_nom_different_ne_declenche_rien(client, baobab):
    autre_prospect(baobab, "Pharmacie du Port")
    assert "Contact multiple possible" not in ouvrir_fiche(client, baobab)


@pytest.mark.django_db
def test_prospect_clos_ne_declenche_rien(client, baobab):
    autre_prospect(baobab, "Garage Baobab", statut=Prospect.Statut.PERDU)
    assert "Contact multiple possible" not in ouvrir_fiche(client, baobab)


@pytest.mark.django_db
def test_meme_commercial_ne_declenche_rien(client, baobab):
    # Deux fiches du même commercial : pas un contact multiple.
    Prospect.objects.create(
        nom="Garage Baobab",
        produit=baobab.produit,
        commercial=baobab.commercial,
        equipe=baobab.equipe,
    )
    assert contacts_en_double(baobab) == []


@pytest.mark.django_db
def test_avertissement_ne_revele_pas_le_nom_de_l_autre_prospect(client, baobab):
    # Même partenaire : l'avertissement se déclenche malgré des noms très différents.
    teranga = Partenaire.objects.get(nom_commercial="Garage Teranga")
    baobab.partenaire = teranga
    baobab.save()
    autre_prospect(baobab, "Dossier Confidentiel", partenaire=teranga)
    contenu = ouvrir_fiche(client, baobab)
    assert "Contact multiple possible" in contenu
    # Le commercial et l'équipe sont visibles, pas le nom du prospect de l'autre équipe.
    assert "Confidentiel" not in contenu
