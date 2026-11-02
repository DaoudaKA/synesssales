"""Tests de la fiche prospect et de la réaffectation sans perte d'historique."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import JournalAudit
from applications.ventes.models import Activite, Prospect, Tache
from applications.ventes.services import reaffecter_prospect

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


def se_connecter(client, email):
    utilisateur = compte(email)
    client.force_login(utilisateur)
    return utilisateur


def adresse(prospect):
    return f"/prospects/{prospect.pk}/"


@pytest.mark.django_db
def test_fiche_exige_la_connexion(client, baobab):
    reponse = client.get(adresse(baobab))
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_commercial_voit_sa_fiche_sans_formulaire(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    reponse = client.get(adresse(baobab))
    assert reponse.status_code == 200
    contenu = reponse.content.decode()
    assert "Garage Baobab" in contenu
    assert "Réaffecter le prospect" not in contenu


@pytest.mark.django_db
def test_prospect_d_une_autre_equipe_est_introuvable(client, baobab):
    se_connecter(client, "commercial3@exemple.com")
    assert client.get(adresse(baobab)).status_code == 404


@pytest.mark.django_db
def test_responsable_data_est_refuse(client, baobab):
    se_connecter(client, "data@exemple.com")
    assert client.get(adresse(baobab)).status_code == 403


@pytest.mark.django_db
def test_chef_d_equipe_voit_le_formulaire(client, baobab):
    se_connecter(client, "chef@exemple.com")
    contenu = client.get(adresse(baobab)).content.decode()
    assert "Réaffecter le prospect" in contenu


@pytest.mark.django_db
def test_reaffectation_conserve_tout_l_historique(client, baobab):
    chef = se_connecter(client, "chef@exemple.com")
    awa, moussa = compte("commercial1@exemple.com"), compte("commercial2@exemple.com")
    Activite.objects.create(prospect=baobab, auteur=awa, type="appel", date=timezone.now())
    a_faire = Tache.objects.create(
        prospect=baobab, responsable=awa, type="relance", echeance=timezone.now()
    )
    faite = Tache.objects.create(
        prospect=baobab, responsable=awa, type="rdv", echeance=timezone.now(), statut="faite"
    )

    reponse = client.post(
        adresse(baobab), {"commercial": moussa.pk, "motif": "Charge de travail"}
    )

    assert reponse.status_code == 302
    baobab.refresh_from_db()
    assert baobab.commercial == moussa
    assert baobab.equipe == moussa.equipe
    # Une ligne d'historique garde qui, de qui vers qui, pourquoi.
    trace = baobab.reaffectations.get()
    assert (trace.ancien_commercial, trace.nouveau_commercial) == (awa, moussa)
    assert trace.auteur == chef
    assert trace.motif == "Charge de travail"
    # L'activité reste au prospect, avec son auteur d'origine.
    assert baobab.activites.get().auteur == awa
    # La relance à faire suit le nouveau commercial ; la tâche déjà faite reste à Awa.
    a_faire.refresh_from_db()
    faite.refresh_from_db()
    assert a_faire.responsable == moussa
    assert faite.responsable == awa


@pytest.mark.django_db
def test_reaffectation_est_journalisee(client, baobab):
    chef = se_connecter(client, "chef@exemple.com")
    client.post(adresse(baobab), {"commercial": compte("commercial2@exemple.com").pk})
    assert JournalAudit.objects.filter(
        utilisateur=chef, action="reaffectation", objet_id=str(baobab.pk)
    ).exists()


@pytest.mark.django_db
def test_historique_affiche_sur_la_fiche(client, baobab):
    se_connecter(client, "chef@exemple.com")
    client.post(
        adresse(baobab),
        {"commercial": compte("commercial2@exemple.com").pk, "motif": "Congé de Awa"},
    )
    contenu = client.get(adresse(baobab)).content.decode()
    assert "Congé de Awa" in contenu


@pytest.mark.django_db
def test_cible_hors_equipe_refusee(client, baobab):
    se_connecter(client, "chef@exemple.com")
    thies = compte("commercial3@exemple.com")
    reponse = client.post(adresse(baobab), {"commercial": thies.pk})
    assert reponse.status_code == 200
    baobab.refresh_from_db()
    assert baobab.commercial == compte("commercial1@exemple.com")
    assert not baobab.reaffectations.exists()


@pytest.mark.django_db
def test_meme_commercial_refuse(client, baobab):
    se_connecter(client, "chef@exemple.com")
    reponse = client.post(adresse(baobab), {"commercial": compte("commercial1@exemple.com").pk})
    assert reponse.status_code == 200
    assert not baobab.reaffectations.exists()


@pytest.mark.django_db
def test_commercial_ne_peut_pas_reaffecter(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    reponse = client.post(adresse(baobab), {"commercial": compte("commercial2@exemple.com").pk})
    assert reponse.status_code == 403
    baobab.refresh_from_db()
    assert baobab.commercial == compte("commercial1@exemple.com")


@pytest.mark.django_db
def test_reaffectations_successives_gardent_chaque_etape(baobab):
    chef = compte("chef@exemple.com")
    awa, moussa = compte("commercial1@exemple.com"), compte("commercial2@exemple.com")
    reaffecter_prospect(baobab, moussa, chef)
    reaffecter_prospect(baobab, awa, chef)
    # Plus récente en premier : Moussa → Awa, puis Awa → Moussa.
    etapes = [(r.ancien_commercial, r.nouveau_commercial) for r in baobab.reaffectations.all()]
    assert etapes == [(moussa, awa), (awa, moussa)]


@pytest.mark.django_db
def test_service_refuse_le_meme_commercial(baobab):
    with pytest.raises(ValueError):
        reaffecter_prospect(baobab, baobab.commercial, compte("chef@exemple.com"))


@pytest.mark.django_db
def test_lien_vers_la_fiche_dans_la_liste(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    contenu = client.get("/prospects/").content.decode()
    assert f'href="/prospects/{baobab.pk}/"' in contenu
