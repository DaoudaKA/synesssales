"""Tests du registre des sources de données : validation tracée et garde d'autorisation."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from applications.collecte.models import SourceDonnees
from applications.collecte.services import (
    ImportInvalide,
    SourceNonAutorisee,
    importer_csv,
    revoquer_source,
    valider_source,
)
from applications.comptes.models import JournalAudit, Role

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"
CSV = b"nom_commercial,ville\nAtelier Test,Dakar\n"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def data(demo):
    return Utilisateur.objects.get(email="data@exemple.com")


@pytest.fixture
def source(db):
    return SourceDonnees.objects.create(nom="Annuaire de test", type="fichier")


def utilisateur_avec_role(email, role):
    personne = Utilisateur.objects.create(email=email, nom=email)
    personne.roles.add(Role.objects.get(nom=role))
    return personne


@pytest.mark.django_db
def test_une_source_neuve_est_refusee_puis_acceptee_apres_validation(source, data):
    with pytest.raises(SourceNonAutorisee):
        importer_csv(CSV, source)
    # La nouvelle exception reste une ImportInvalide : les écrans existants la traitent.
    assert issubclass(SourceNonAutorisee, ImportInvalide)

    valider_source(source, data, "Courriel de SYNESS du 04/11/2026")
    collecte, erreurs = importer_csv(CSV, source)
    assert collecte.nb_fiches == 1 and erreurs == []


@pytest.mark.django_db
def test_validation_enregistre_qui_quand_et_sur_quelle_base(source, data):
    valider_source(source, data, "  Courriel de SYNESS  ")
    source.refresh_from_db()
    assert source.conditions_validees is True
    assert source.validee_par == data
    assert source.date_validation is not None
    assert source.reference_validation == "Courriel de SYNESS"


@pytest.mark.django_db
def test_validation_sans_reference_est_impossible(source, data):
    for vide in ("", "   ", None):
        with pytest.raises(ValueError):
            valider_source(source, data, vide)
    source.refresh_from_db()
    assert source.conditions_validees is False


@pytest.mark.django_db
def test_revocation_motivee_garde_la_trace_et_bloque_les_imports(source, data):
    valider_source(source, data, "Courriel de SYNESS")
    with pytest.raises(ValueError):
        revoquer_source(source, " ")
    revoquer_source(source, "Conditions d'usage modifiées")
    source.refresh_from_db()
    assert source.conditions_validees is False
    assert source.reference_validation == "Courriel de SYNESS"  # trace conservée
    with pytest.raises(SourceNonAutorisee):
        importer_csv(CSV, source)


@pytest.mark.django_db
def test_ecran_des_sources_selon_les_droits(client, demo):
    assert client.get("/sources/").status_code == 302  # anonyme
    # Responsable data, administrateur et analyste consultent ; le commercial non.
    analyste = utilisateur_avec_role("analyste@exemple.com", "Analyste ou responsable métier")
    admin = utilisateur_avec_role("admin-test@exemple.com", "Administrateur système")
    for email in ("data@exemple.com",):
        client.force_login(Utilisateur.objects.get(email=email))
        assert client.get("/sources/").status_code == 200
    for personne in (analyste, admin):
        client.force_login(personne)
        assert client.get("/sources/").status_code == 200
    client.force_login(Utilisateur.objects.get(email="commercial1@exemple.com"))
    assert client.get("/sources/").status_code == 403


@pytest.mark.django_db
def test_creation_d_une_source_par_le_responsable_data(client, data):
    client.force_login(data)
    avant = JournalAudit.objects.count()
    reponse = client.post(
        "/sources/nouvelle/", {"nom": "Annuaire public", "type": "site", "url": ""}
    )
    assert reponse.status_code == 302
    source = SourceDonnees.objects.get(nom="Annuaire public")
    assert source.conditions_validees is False  # jamais autorisée à la création
    assert JournalAudit.objects.count() == avant + 1


@pytest.mark.django_db
def test_creation_refusee_a_l_administrateur_en_lecture_seule(client, demo):
    admin = utilisateur_avec_role("admin-test@exemple.com", "Administrateur système")
    client.force_login(admin)
    assert client.post("/sources/nouvelle/", {"nom": "X", "type": "", "url": ""}).status_code == 403
    assert not SourceDonnees.objects.filter(nom="X").exists()


@pytest.mark.django_db
def test_validation_par_l_ecran(client, data, source):
    client.force_login(data)
    adresse = f"/sources/{source.pk}/validation/"
    assert client.get(adresse).status_code == 405  # une action se fait en POST
    # Sans référence : refusée.
    client.post(adresse, {"reference": ""})
    source.refresh_from_db()
    assert source.conditions_validees is False

    avant = JournalAudit.objects.count()
    reponse = client.post(adresse, {"reference": "Courriel de SYNESS"})
    assert reponse.status_code == 302
    source.refresh_from_db()
    assert source.conditions_validees is True and source.validee_par == data
    assert JournalAudit.objects.count() == avant + 1


@pytest.mark.django_db
def test_validation_refusee_a_qui_n_a_pas_le_droit_de_modifier(client, demo, source):
    admin = utilisateur_avec_role("admin-test@exemple.com", "Administrateur système")
    client.force_login(admin)
    reponse = client.post(f"/sources/{source.pk}/validation/", {"reference": "Réf"})
    assert reponse.status_code == 403
    source.refresh_from_db()
    assert source.conditions_validees is False


@pytest.mark.django_db
def test_revocation_par_l_ecran(client, data, source):
    valider_source(source, data, "Courriel de SYNESS")
    client.force_login(data)
    adresse = f"/sources/{source.pk}/revocation/"
    client.post(adresse, {"motif": ""})
    source.refresh_from_db()
    assert source.conditions_validees is True  # motif manquant : rien ne change

    client.post(adresse, {"motif": "Conditions modifiées"})
    source.refresh_from_db()
    assert source.conditions_validees is False
