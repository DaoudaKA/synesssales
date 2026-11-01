"""Tests de l'import CSV : règles de la source, lignes en erreur, provenance, écrans."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from applications.collecte.models import AlerteDoublon, Collecte, Provenance, SourceDonnees
from applications.collecte.services import ImportInvalide, importer_csv
from applications.comptes.models import JournalAudit
from applications.partenaires.models import Localisation, Partenaire

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"

CSV_VALIDE = (
    "nom_commercial,categorie,ville,telephone,email,service\n"
    "Atelier Kër,Garage,Dakar,771234567,ker@exemple.sn,Vidange\n"
    "Pneus Diop,,Thiès,,,\n"
)


@pytest.fixture
def source(db):
    return SourceDonnees.objects.create(nom="Annuaire test", conditions_validees=True)


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


def se_connecter(client, email):
    client.force_login(Utilisateur.objects.get(email=email))


def televerser(client, source, contenu=CSV_VALIDE, nom="fiches.csv"):
    fichier = SimpleUploadedFile(nom, contenu.encode(), content_type="text/csv")
    return client.post("/collectes/importer/", {"source": source.pk, "fichier": fichier})


# --- Le service d'import -------------------------------------------------


@pytest.mark.django_db
def test_import_complet_avec_provenance(source):
    collecte, erreurs = importer_csv(CSV_VALIDE.encode(), source)
    assert erreurs == []
    assert collecte.statut == Collecte.Statut.TERMINEE
    assert (collecte.nb_fiches, collecte.nb_erreurs) == (2, 0)
    fiche = Partenaire.objects.get(nom_commercial="Atelier Kër")
    assert fiche.statut_verification == Partenaire.StatutVerification.A_VERIFIER
    assert fiche.categorie.nom == "Garage"
    assert fiche.localisations.get().pays == "Sénégal"  # pays par défaut
    assert fiche.contacts.count() == 2
    assert fiche.services.get().libelle == "Vidange"
    provenance = Provenance.objects.get(partenaire=fiche, champ="ville")
    assert provenance.valeur == "Dakar"
    assert provenance.source == source
    assert provenance.collecte == collecte
    assert provenance.niveau == Provenance.Niveau.COLLECTE


@pytest.mark.django_db
def test_lignes_en_erreur_n_empechent_pas_les_autres(source):
    contenu = (
        "nom_commercial,email\n"
        "Bon Garage,ok@exemple.sn\n"
        ",sans-nom@exemple.sn\n"
        "Autre Garage,pas-un-email\n"
    )
    collecte, erreurs = importer_csv(contenu.encode(), source)
    assert [numero for numero, _ in erreurs] == [3, 4]
    assert (collecte.nb_fiches, collecte.nb_erreurs) == (1, 2)
    assert collecte.statut == Collecte.Statut.TERMINEE
    assert Partenaire.objects.filter(nom_commercial="Bon Garage").exists()
    # La ligne 4 a échoué en entier : la fiche n'est pas restée à moitié créée.
    assert not Partenaire.objects.filter(nom_commercial="Autre Garage").exists()


@pytest.mark.django_db
def test_import_entierement_en_erreur(source):
    contenu = "nom_commercial\n\n,\n"
    collecte, _ = importer_csv("nom_commercial,email\n,x@exemple.sn\n".encode(), source)
    assert collecte.statut == Collecte.Statut.EN_ERREUR
    assert collecte.nb_fiches == 0
    assert contenu  # le contenu ci-dessus n'est pas utilisé : seul le fichier précédent compte


@pytest.mark.django_db
def test_separateur_point_virgule(source):
    contenu = "nom_commercial;ville\nGarage Point-Virgule;Thiès\n"
    collecte, erreurs = importer_csv(contenu.encode(), source)
    assert erreurs == []
    assert collecte.nb_fiches == 1


@pytest.mark.django_db
def test_colonne_obligatoire_absente(source):
    with pytest.raises(ImportInvalide):
        importer_csv("ville\nDakar\n".encode(), source)
    assert not Collecte.objects.exists()


@pytest.mark.django_db
def test_source_non_validee_refusee():
    source = SourceDonnees.objects.create(nom="Source douteuse", conditions_validees=False)
    with pytest.raises(ImportInvalide):
        importer_csv(CSV_VALIDE.encode(), source)
    assert not Collecte.objects.exists()
    assert not Partenaire.objects.exists()


@pytest.mark.django_db
def test_fichier_non_utf8_refuse(source):
    with pytest.raises(ImportInvalide):
        importer_csv("nom_commercial\nGarage Éclair\n".encode("latin-1"), source)


@pytest.mark.django_db
def test_fichier_trop_long_refuse(source):
    contenu = "nom_commercial\n" + "Garage\n" * 1001
    with pytest.raises(ImportInvalide):
        importer_csv(contenu.encode(), source)
    assert not Partenaire.objects.exists()


@pytest.mark.django_db
def test_import_declenche_la_detection_des_doublons(source):
    existante = Partenaire.objects.create(nom_commercial="Mécanique Sahel")
    Localisation.objects.create(partenaire=existante, pays="Sénégal", ville="Dakar")
    importer_csv("nom_commercial,ville\nMecanique Sahel,Dakar\n".encode(), source)
    assert AlerteDoublon.objects.count() == 1


# --- Les écrans ----------------------------------------------------------


@pytest.mark.django_db
def test_ecrans_exigent_la_connexion(client):
    for adresse in ("/collectes/", "/collectes/importer/"):
        reponse = client.get(adresse)
        assert reponse.status_code == 302
        assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_commercial_est_refuse(client, demo):
    se_connecter(client, "commercial1@exemple.com")
    assert client.get("/collectes/").status_code == 403
    assert client.get("/collectes/importer/").status_code == 403


@pytest.mark.django_db
def test_responsable_data_importe_un_fichier(client, demo):
    se_connecter(client, "data@exemple.com")
    source = SourceDonnees.objects.get(nom="Annuaire de démonstration")
    reponse = televerser(client, source)
    assert reponse.status_code == 200
    assert "2 fiche(s) importée(s)" in reponse.content.decode()
    assert Partenaire.objects.filter(nom_commercial="Pneus Diop").exists()
    assert JournalAudit.objects.filter(action="import").exists()


@pytest.mark.django_db
def test_extension_refusee(client, demo):
    se_connecter(client, "data@exemple.com")
    source = SourceDonnees.objects.get(nom="Annuaire de démonstration")
    televerser(client, source, nom="fiches.txt")
    assert not Collecte.objects.exists()


@pytest.mark.django_db
def test_source_non_validee_absente_du_formulaire(client, demo):
    se_connecter(client, "data@exemple.com")
    douteuse = SourceDonnees.objects.get(nom="Site non vérifié")
    reponse = televerser(client, douteuse)
    assert reponse.status_code == 200
    assert not Collecte.objects.exists()


@pytest.mark.django_db
def test_liste_des_collectes(client, demo):
    se_connecter(client, "data@exemple.com")
    source = SourceDonnees.objects.get(nom="Annuaire de démonstration")
    televerser(client, source)
    contenu = client.get("/collectes/").content.decode()
    assert "Annuaire de démonstration" in contenu
    assert "Terminée" in contenu


@pytest.mark.django_db
def test_lien_collectes_selon_le_profil(client, demo):
    se_connecter(client, "data@exemple.com")
    assert 'href="/collectes/"' in client.get("/").content.decode()
    se_connecter(client, "commercial1@exemple.com")
    assert 'href="/collectes/"' not in client.get("/").content.decode()
