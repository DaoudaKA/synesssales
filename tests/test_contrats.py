"""Tests du circuit des contrats : soumission, validation, refus avec motif."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import JournalAudit, Role
from applications.ventes.models import Contrat, Prospect

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def baobab(demo):
    """Prospect de démonstration suivi par commercial1 (équipe Dakar)."""
    return Prospect.objects.get(nom="Garage Baobab")


@pytest.fixture
def responsable(demo):
    """Un Responsable commercial (droit « LV » sur les contrats), sans prospect propre."""
    utilisateur = Utilisateur.objects.create(
        email="responsable@exemple.com", nom="Responsable Test"
    )
    utilisateur.roles.add(Role.objects.get(nom="Responsable commercial"))
    return utilisateur


@pytest.fixture
def soumis(baobab):
    """Un contrat soumis sur Garage Baobab."""
    return Contrat.objects.create(prospect=baobab, date_signature=timezone.localdate())


def compte(email):
    return Utilisateur.objects.get(email=email)


def se_connecter(client, utilisateur):
    client.force_login(utilisateur)
    return utilisateur


def jour(decalage=0):
    """Une date au format du champ HTML « date »."""
    return (timezone.localdate() + datetime.timedelta(days=decalage)).isoformat()


def adresse_soumission(prospect):
    return f"/prospects/{prospect.pk}/contrats/nouveau/"


def adresse_decision(contrat):
    return f"/contrats/{contrat.pk}/decision/"


@pytest.mark.django_db
def test_commercial_soumet_un_contrat(client, baobab):
    awa = se_connecter(client, compte("commercial1@exemple.com"))
    reponse = client.post(adresse_soumission(baobab), {"date_signature": jour(-1)})
    assert reponse.status_code == 302
    contrat = baobab.contrats.get()
    assert contrat.statut_validation == Contrat.StatutValidation.SOUMIS
    assert JournalAudit.objects.filter(
        utilisateur=awa, action="creation", objet_id=str(contrat.pk)
    ).exists()


@pytest.mark.django_db
def test_date_de_signature_future_refusee(client, baobab):
    se_connecter(client, compte("commercial1@exemple.com"))
    reponse = client.post(adresse_soumission(baobab), {"date_signature": jour(3)})
    assert reponse.status_code == 200
    assert not baobab.contrats.exists()


@pytest.mark.django_db
def test_un_seul_contrat_en_cours(client, baobab, soumis):
    se_connecter(client, compte("commercial1@exemple.com"))
    reponse = client.post(adresse_soumission(baobab), {"date_signature": jour()})
    assert reponse.status_code == 200
    assert baobab.contrats.count() == 1


@pytest.mark.django_db
def test_nouvelle_soumission_possible_apres_un_refus(client, baobab, soumis):
    soumis.statut_validation = Contrat.StatutValidation.REFUSE
    soumis.save()
    se_connecter(client, compte("commercial1@exemple.com"))
    reponse = client.post(adresse_soumission(baobab), {"date_signature": jour()})
    assert reponse.status_code == 302
    assert baobab.contrats.count() == 2


@pytest.mark.django_db
def test_prospect_d_une_autre_equipe_est_introuvable(client, baobab):
    se_connecter(client, compte("commercial3@exemple.com"))
    reponse = client.post(adresse_soumission(baobab), {"date_signature": jour()})
    assert reponse.status_code == 404


@pytest.mark.django_db
def test_chef_d_equipe_ne_peut_pas_soumettre(client, baobab):
    # La matrice ne lui donne que « L* » sur les contrats : consultation seulement.
    se_connecter(client, compte("chef@exemple.com"))
    reponse = client.post(adresse_soumission(baobab), {"date_signature": jour()})
    assert reponse.status_code == 403
    assert not baobab.contrats.exists()


@pytest.mark.django_db
def test_responsable_valide_le_contrat(client, baobab, soumis, responsable):
    se_connecter(client, responsable)
    reponse = client.post(adresse_decision(soumis), {"decision": "valider"})
    assert reponse.status_code == 302
    soumis.refresh_from_db()
    baobab.refresh_from_db()
    assert soumis.statut_validation == Contrat.StatutValidation.VALIDE
    assert soumis.valide_par == responsable
    assert baobab.statut == Prospect.Statut.GAGNE
    assert JournalAudit.objects.filter(
        utilisateur=responsable, action="validation", objet_id=str(soumis.pk)
    ).exists()


@pytest.mark.django_db
def test_refus_sans_motif_impossible(client, soumis, responsable):
    se_connecter(client, responsable)
    reponse = client.post(adresse_decision(soumis), {"decision": "refuser", "motif": "  "})
    assert reponse.status_code == 200
    soumis.refresh_from_db()
    assert soumis.statut_validation == Contrat.StatutValidation.SOUMIS


@pytest.mark.django_db
def test_refus_avec_motif(client, baobab, soumis, responsable):
    statut_avant = baobab.statut
    se_connecter(client, responsable)
    reponse = client.post(
        adresse_decision(soumis), {"decision": "refuser", "motif": "Pièces manquantes"}
    )
    assert reponse.status_code == 302
    soumis.refresh_from_db()
    baobab.refresh_from_db()
    assert soumis.statut_validation == Contrat.StatutValidation.REFUSE
    assert soumis.motif_refus == "Pièces manquantes"
    assert soumis.valide_par == responsable
    assert baobab.statut == statut_avant  # un refus ne change pas le statut du prospect
    assert JournalAudit.objects.filter(
        utilisateur=responsable, action="refus", objet_id=str(soumis.pk)
    ).exists()


@pytest.mark.django_db
def test_commercial_ne_peut_pas_decider(client, soumis):
    se_connecter(client, compte("commercial1@exemple.com"))
    assert client.get(adresse_decision(soumis)).status_code == 403
    assert client.post(adresse_decision(soumis), {"decision": "valider"}).status_code == 403
    soumis.refresh_from_db()
    assert soumis.statut_validation == Contrat.StatutValidation.SOUMIS


@pytest.mark.django_db
def test_chef_d_equipe_ne_peut_pas_decider(client, soumis):
    se_connecter(client, compte("chef@exemple.com"))
    assert client.post(adresse_decision(soumis), {"decision": "valider"}).status_code == 403


@pytest.mark.django_db
def test_contrat_deja_decide_ne_change_plus(client, soumis, responsable):
    se_connecter(client, responsable)
    client.post(adresse_decision(soumis), {"decision": "valider"})
    client.post(adresse_decision(soumis), {"decision": "refuser", "motif": "Trop tard"})
    soumis.refresh_from_db()
    assert soumis.statut_validation == Contrat.StatutValidation.VALIDE
    assert soumis.motif_refus == ""


@pytest.mark.django_db
def test_on_ne_valide_pas_son_propre_contrat(client, baobab, soumis, responsable):
    # Séparation des rôles : le validateur est ici le commercial du prospect.
    baobab.commercial = responsable
    baobab.save()
    se_connecter(client, responsable)
    assert client.post(adresse_decision(soumis), {"decision": "valider"}).status_code == 403


@pytest.mark.django_db
def test_decision_inconnue_refusee(client, soumis, responsable):
    se_connecter(client, responsable)
    assert client.post(adresse_decision(soumis), {"decision": "autre"}).status_code == 400
    soumis.refresh_from_db()
    assert soumis.statut_validation == Contrat.StatutValidation.SOUMIS


@pytest.mark.django_db
def test_liste_des_contrats_a_valider(client, baobab, soumis, responsable):
    awa = compte("commercial1@exemple.com")
    autre = Prospect.objects.create(
        nom="Pharmacie du Port", produit=baobab.produit, commercial=awa, equipe=awa.equipe
    )
    Contrat.objects.create(
        prospect=autre,
        date_signature=timezone.localdate(),
        statut_validation=Contrat.StatutValidation.VALIDE,
    )
    se_connecter(client, responsable)
    contenu = client.get("/contrats/a-valider/").content.decode()
    assert "Garage Baobab" in contenu
    assert "Pharmacie du Port" not in contenu  # déjà validé : plus à valider
    assert "Examiner" in contenu


@pytest.mark.django_db
def test_liste_refusee_au_commercial(client, demo):
    se_connecter(client, compte("commercial1@exemple.com"))
    assert client.get("/contrats/a-valider/").status_code == 403


@pytest.mark.django_db
def test_fiche_propose_la_soumission_au_commercial(client, baobab):
    se_connecter(client, compte("commercial1@exemple.com"))
    contenu = client.get(f"/prospects/{baobab.pk}/").content.decode()
    assert "Soumettre un contrat" in contenu
    assert "Examiner" not in contenu  # seul un validateur examine un contrat
