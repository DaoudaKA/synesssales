"""Tests de la vérification d'une fiche partenaire."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.collecte.models import Verification
from applications.comptes.models import JournalAudit
from applications.partenaires.models import Partenaire

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def a_verifier(demo):
    return Partenaire.objects.get(nom_commercial="Auto Service Thiès")


@pytest.fixture
def verifie(demo):
    return Partenaire.objects.get(nom_commercial="Garage Teranga")


def se_connecter(client, email):
    utilisateur = Utilisateur.objects.get(email=email)
    client.force_login(utilisateur)
    return utilisateur


def adresse(partenaire):
    return f"/partenaires/{partenaire.pk}/verifier/"


@pytest.mark.django_db
def test_ecran_exige_la_connexion(client, a_verifier):
    reponse = client.get(adresse(a_verifier))
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_commercial_ne_peut_pas_verifier(client, a_verifier):
    se_connecter(client, "commercial1@exemple.com")
    assert client.get(adresse(a_verifier)).status_code == 403
    assert client.post(adresse(a_verifier), {"resultat": "conforme"}).status_code == 403
    assert not Verification.objects.exists()


@pytest.mark.django_db
def test_responsable_data_voit_le_formulaire(client, a_verifier):
    se_connecter(client, "data@exemple.com")
    reponse = client.get(adresse(a_verifier))
    assert reponse.status_code == 200
    assert "Auto Service Thiès" in reponse.content.decode()


@pytest.mark.django_db
def test_fiche_conforme_devient_verifiee(client, a_verifier):
    utilisateur = se_connecter(client, "data@exemple.com")
    reponse = client.post(adresse(a_verifier), {"resultat": "conforme"})
    assert reponse.status_code == 302
    a_verifier.refresh_from_db()
    assert a_verifier.statut_verification == Partenaire.StatutVerification.VERIFIE
    assert a_verifier.date_derniere_verification is not None
    verification = a_verifier.verifications.get()
    assert verification.utilisateur == utilisateur
    assert JournalAudit.objects.filter(
        utilisateur=utilisateur, action="verification", objet_id=str(a_verifier.pk)
    ).exists()


@pytest.mark.django_db
def test_fiche_rejetee(client, a_verifier):
    se_connecter(client, "data@exemple.com")
    client.post(adresse(a_verifier), {"resultat": "rejete", "commentaire": "Garage fermé"})
    a_verifier.refresh_from_db()
    assert a_verifier.statut_verification == Partenaire.StatutVerification.REJETE
    assert a_verifier.verifications.get().commentaire == "Garage fermé"


@pytest.mark.django_db
def test_fiche_a_corriger_retourne_a_verifier(client, verifie):
    se_connecter(client, "data@exemple.com")
    client.post(adresse(verifie), {"resultat": "a_corriger", "commentaire": "Téléphone faux"})
    verifie.refresh_from_db()
    assert verifie.statut_verification == Partenaire.StatutVerification.A_VERIFIER
    assert verifie.verifications.count() == 1


@pytest.mark.django_db
def test_commentaire_obligatoire_si_non_conforme(client, a_verifier):
    se_connecter(client, "data@exemple.com")
    reponse = client.post(adresse(a_verifier), {"resultat": "rejete", "commentaire": " "})
    assert reponse.status_code == 200
    a_verifier.refresh_from_db()
    assert a_verifier.statut_verification == Partenaire.StatutVerification.A_VERIFIER
    assert not Verification.objects.exists()


@pytest.mark.django_db
def test_fiche_inconnue(client, demo):
    se_connecter(client, "data@exemple.com")
    assert client.get("/partenaires/999999/verifier/").status_code == 404


@pytest.mark.django_db
def test_historique_affiche(client, a_verifier):
    se_connecter(client, "data@exemple.com")
    client.post(
        adresse(a_verifier), {"resultat": "a_corriger", "commentaire": "Adresse incomplète"}
    )
    client.post(adresse(a_verifier), {"resultat": "conforme"})
    contenu = client.get(adresse(a_verifier)).content.decode()
    assert "Adresse incomplète" in contenu
    assert a_verifier.verifications.count() == 2


@pytest.mark.django_db
def test_lien_verifier_selon_le_profil(client, a_verifier):
    se_connecter(client, "data@exemple.com")
    assert adresse(a_verifier) in client.get("/partenaires/").content.decode()
    se_connecter(client, "commercial1@exemple.com")
    assert adresse(a_verifier) not in client.get("/partenaires/").content.decode()
