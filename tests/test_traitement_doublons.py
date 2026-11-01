"""Tests du traitement des doublons : rejet et fusion sans perte."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.collecte.models import AlerteDoublon, Verification
from applications.comptes.models import JournalAudit
from applications.partenaires.models import Contact, Localisation, Partenaire, ServicePropose
from applications.partenaires.services import detecter_doublons
from applications.ventes.models import Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"

# Les noms ci-dessous n'existent pas dans les données de démonstration
# ("Garage Teranga", etc.) : sinon la détection créerait des alertes parasites
# avec ces fiches et fausserait les résultats.
NOM = "Mécanique Sahel"
NOM_VARIANTE = "Mecanique Sahel"  # sans accent : se normalise comme NOM (score 1,00)


@pytest.fixture
def demo(db):
    """Charge les comptes de démonstration (data@, commercial1@, etc.)."""
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def se_connecter(client, email):
    """Connecte le client de test avec le compte demandé."""
    utilisateur = Utilisateur.objects.get(email=email)
    client.force_login(utilisateur)
    return utilisateur


def creer(nom, ville="Dakar"):
    """Crée une fiche partenaire avec une localisation."""
    fiche = Partenaire.objects.create(nom_commercial=nom)
    Localisation.objects.create(partenaire=fiche, pays="Sénégal", ville=ville)
    return fiche


def fusion(client, alerte, garder):
    """Demande la fusion de l'alerte en gardant la fiche « a » ou « b »."""
    return client.post(f"/partenaires/doublons/{alerte.pk}/fusionner/", {"conservee": garder})


def rejet(client, alerte):
    """Demande le rejet de l'alerte."""
    return client.post(f"/partenaires/doublons/{alerte.pk}/rejeter/")


@pytest.fixture
def paire(demo):
    """Deux fiches presque identiques et l'alerte de doublon qui les relie."""
    fiche_a = creer(NOM)
    fiche_b = creer(NOM_VARIANTE)
    alerte = detecter_doublons(fiche_b)[0]
    return fiche_a, fiche_b, alerte


@pytest.mark.django_db
def test_rejet_ecarte_l_alerte(client, paire):
    _, _, alerte = paire
    utilisateur = se_connecter(client, "data@exemple.com")
    reponse = rejet(client, alerte)
    assert reponse.status_code == 302
    assert reponse.url == "/partenaires/doublons/"
    alerte.refresh_from_db()
    assert alerte.statut == AlerteDoublon.Statut.REJETEE
    # L'alerte rejetée n'apparaît plus dans l'écran des doublons.
    page = client.get("/partenaires/doublons/").content.decode()
    assert NOM_VARIANTE not in page
    assert JournalAudit.objects.filter(utilisateur=utilisateur, action="rejet_doublon").exists()


@pytest.mark.django_db
def test_commercial_ne_peut_pas_rejeter(client, paire):
    _, _, alerte = paire
    se_connecter(client, "commercial1@exemple.com")
    assert rejet(client, alerte).status_code == 403
    alerte.refresh_from_db()
    assert alerte.statut == AlerteDoublon.Statut.OUVERTE


@pytest.mark.django_db
def test_commercial_ne_peut_pas_fusionner(client, paire):
    _, _, alerte = paire
    se_connecter(client, "commercial1@exemple.com")
    assert fusion(client, alerte, "a").status_code == 403
    alerte.refresh_from_db()
    assert alerte.statut == AlerteDoublon.Statut.OUVERTE


@pytest.mark.django_db
def test_rejet_exige_une_requete_post(client, paire):
    _, _, alerte = paire
    se_connecter(client, "data@exemple.com")
    assert client.get(f"/partenaires/doublons/{alerte.pk}/rejeter/").status_code == 405


@pytest.mark.django_db
def test_fusion_transfere_tout_sans_rien_perdre(client, paire):
    fiche_a, fiche_b, alerte = paire
    # La fiche A a déjà le téléphone ; la fiche B a le même et en plus un e-mail.
    Contact.objects.create(partenaire=fiche_a, type="tel", valeur="771")
    Contact.objects.create(partenaire=fiche_b, type="tel", valeur="771")
    Contact.objects.create(partenaire=fiche_b, type="email", valeur="b@exemple.sn")
    ServicePropose.objects.create(partenaire=fiche_b, libelle="Vidange")
    Localisation.objects.create(partenaire=fiche_b, pays="Sénégal", ville="Thiès")
    Verification.objects.create(partenaire=fiche_b, resultat="conforme")
    # Un prospect de démonstration est rattaché à la fiche B.
    prospect = Prospect.objects.first()
    prospect.partenaire = fiche_b
    prospect.save()
    utilisateur = se_connecter(client, "data@exemple.com")

    assert fusion(client, alerte, "a").status_code == 302

    # Le téléphone commun n'est pas dupliqué : 2 contacts (tél + e-mail).
    assert fiche_a.contacts.count() == 2
    assert fiche_a.services.count() == 1
    # Dakar était déjà là, Thiès est ajoutée.
    assert fiche_a.localisations.count() == 2
    assert fiche_a.verifications.count() == 1
    prospect.refresh_from_db()
    assert prospect.partenaire == fiche_a
    # La fiche B n'est pas supprimée : elle pointe vers la fiche A.
    fiche_b.refresh_from_db()
    assert fiche_b.fusionnee_dans == fiche_a
    alerte.refresh_from_db()
    assert alerte.statut == AlerteDoublon.Statut.FUSIONNEE
    assert JournalAudit.objects.filter(utilisateur=utilisateur, action="fusion").exists()


@pytest.mark.django_db
def test_fusion_en_gardant_la_fiche_b(client, paire):
    fiche_a, fiche_b, alerte = paire
    Contact.objects.create(partenaire=fiche_a, type="email", valeur="a@exemple.sn")
    se_connecter(client, "data@exemple.com")
    fusion(client, alerte, "b")
    fiche_a.refresh_from_db()
    # Cette fois c'est la fiche A qui est absorbée et son e-mail passe à B.
    assert fiche_a.fusionnee_dans == fiche_b
    assert fiche_b.contacts.count() == 1


@pytest.mark.django_db
def test_fusion_remplit_les_champs_vides(client, paire):
    fiche_a, fiche_b, alerte = paire
    fiche_b.description = "Atelier mécanique"
    fiche_b.save()
    se_connecter(client, "data@exemple.com")
    fusion(client, alerte, "a")
    fiche_a.refresh_from_db()
    # La description vide de A est complétée par celle de B.
    assert fiche_a.description == "Atelier mécanique"


@pytest.mark.django_db
def test_fiche_a_conserver_invalide(client, paire):
    _, _, alerte = paire
    se_connecter(client, "data@exemple.com")
    assert fusion(client, alerte, "x").status_code == 400
    alerte.refresh_from_db()
    assert alerte.statut == AlerteDoublon.Statut.OUVERTE


@pytest.mark.django_db
def test_alerte_deja_traitee_est_introuvable(client, paire):
    _, _, alerte = paire
    se_connecter(client, "data@exemple.com")
    rejet(client, alerte)
    # Une alerte rejetée ne peut plus être fusionnée : 404.
    assert fusion(client, alerte, "a").status_code == 404


@pytest.mark.django_db
def test_fiche_absorbee_disparait_de_la_liste(client, paire):
    _, fiche_b, alerte = paire
    fiche_b.nom_commercial = "Mecanique Sahel Annexe"
    fiche_b.save()
    se_connecter(client, "data@exemple.com")
    assert "Annexe" in client.get("/partenaires/").content.decode()
    fusion(client, alerte, "a")
    assert "Annexe" not in client.get("/partenaires/").content.decode()


@pytest.mark.django_db
def test_autres_alertes_de_la_fiche_absorbee_sont_recalculees(client, demo):
    # Trois fiches identiques : A-B, A-C et B-C sont toutes des doublons.
    fiche_a, fiche_b, fiche_c = (creer(NOM) for _ in range(3))
    detecter_doublons(fiche_b)
    detecter_doublons(fiche_c)
    alerte = AlerteDoublon.objects.get(partenaire_a=fiche_a, partenaire_b=fiche_b)
    se_connecter(client, "data@exemple.com")
    fusion(client, alerte, "a")
    # B est absorbée dans A : l'alerte B-C disparaît, il reste seulement A-C.
    ouvertes = AlerteDoublon.objects.filter(statut=AlerteDoublon.Statut.OUVERTE)
    assert list(ouvertes.values_list("partenaire_a", "partenaire_b")) == [
        (fiche_a.pk, fiche_c.pk)
    ]


@pytest.mark.django_db
def test_fiche_fusionnee_n_est_plus_comparee(client, paire):
    fiche_a, _, alerte = paire
    se_connecter(client, "data@exemple.com")
    fusion(client, alerte, "a")
    nouvelle = creer(NOM)
    alertes = detecter_doublons(nouvelle)
    # La fiche absorbée (B) est ignorée : seule la fiche A est comparée.
    assert {(x.partenaire_a_id, x.partenaire_b_id) for x in alertes} == {
        (fiche_a.pk, nouvelle.pk)
    }


@pytest.mark.django_db
def test_boutons_de_traitement_affiches(client, paire):
    _, _, alerte = paire
    se_connecter(client, "data@exemple.com")
    contenu = client.get("/partenaires/doublons/").content.decode()
    assert f"/partenaires/doublons/{alerte.pk}/fusionner/" in contenu
    assert f"/partenaires/doublons/{alerte.pk}/rejeter/" in contenu
