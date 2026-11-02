"""Tests des écrans d'activités et de relances."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import JournalAudit
from applications.ventes.models import Activite, Prospect, Tache

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


def saisie(moment):
    """Écrit un instant comme le fait le champ HTML « datetime-local »."""
    return timezone.localtime(moment).strftime("%Y-%m-%dT%H:%M")


def il_y_a(**duree):
    return timezone.now() - datetime.timedelta(**duree)


def dans(**duree):
    return timezone.now() + datetime.timedelta(**duree)


def adresse_activite(prospect):
    return f"/prospects/{prospect.pk}/activites/nouvelle/"


def adresse_tache(prospect):
    return f"/prospects/{prospect.pk}/taches/nouvelle/"


@pytest.mark.django_db
def test_commercial_consigne_une_activite(client, baobab):
    awa = se_connecter(client, "commercial1@exemple.com")
    reponse = client.post(
        adresse_activite(baobab),
        {"type": "appel", "date": saisie(il_y_a(hours=1)), "resultat": "Intéressé"},
    )
    assert reponse.status_code == 302
    activite = baobab.activites.get(resultat="Intéressé")
    assert activite.auteur == awa
    assert JournalAudit.objects.filter(
        utilisateur=awa, action="creation", objet_id=str(activite.pk)
    ).exists()


@pytest.mark.django_db
def test_premiere_activite_passe_le_prospect_a_contacte(client, demo):
    awa = compte("commercial1@exemple.com")
    neuf = Prospect.objects.create(
        nom="Prospect Neuf",
        produit=Prospect.objects.get(nom="Garage Baobab").produit,
        commercial=awa,
        equipe=awa.equipe,
        statut=Prospect.Statut.NOUVEAU,
    )
    se_connecter(client, "commercial1@exemple.com")
    client.post(adresse_activite(neuf), {"type": "visite", "date": saisie(il_y_a(hours=2))})
    neuf.refresh_from_db()
    assert neuf.statut == Prospect.Statut.CONTACTE


@pytest.mark.django_db
def test_activite_dans_le_futur_refusee(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    reponse = client.post(
        adresse_activite(baobab), {"type": "appel", "date": saisie(dans(days=2))}
    )
    assert reponse.status_code == 200
    assert not Activite.objects.filter(prospect=baobab).exists()


@pytest.mark.django_db
def test_formulaire_activite_s_affiche(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    reponse = client.get(adresse_activite(baobab))
    assert reponse.status_code == 200
    assert "Consigner une activité" in reponse.content.decode()


@pytest.mark.django_db
def test_prospect_d_une_autre_equipe_est_introuvable(client, baobab):
    se_connecter(client, "commercial3@exemple.com")
    reponse = client.post(
        adresse_activite(baobab), {"type": "appel", "date": saisie(il_y_a(hours=1))}
    )
    assert reponse.status_code == 404
    assert not Activite.objects.filter(prospect=baobab).exists()


@pytest.mark.django_db
def test_responsable_data_ne_peut_rien_saisir(client, baobab):
    se_connecter(client, "data@exemple.com")
    reponse = client.post(
        adresse_activite(baobab), {"type": "appel", "date": saisie(il_y_a(hours=1))}
    )
    assert reponse.status_code in (403, 404)
    assert not Activite.objects.filter(prospect=baobab).exists()


@pytest.mark.django_db
def test_commercial_planifie_une_relance(client, baobab):
    awa = se_connecter(client, "commercial1@exemple.com")
    reponse = client.post(
        adresse_tache(baobab), {"type": "relance", "echeance": saisie(dans(days=2))}
    )
    assert reponse.status_code == 302
    tache = baobab.taches.get()
    assert tache.responsable == awa  # confiée au commercial du prospect
    assert tache.statut == Tache.Statut.A_FAIRE


@pytest.mark.django_db
def test_echeance_dans_le_passe_refusee(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    reponse = client.post(
        adresse_tache(baobab), {"type": "relance", "echeance": saisie(il_y_a(days=2))}
    )
    assert reponse.status_code == 200
    assert not baobab.taches.exists()


@pytest.mark.django_db
def test_marquer_une_tache_comme_faite(client, baobab):
    awa = se_connecter(client, "commercial1@exemple.com")
    tache = Tache.objects.create(
        prospect=baobab, responsable=awa, type="relance", echeance=dans(days=1)
    )
    # Une action qui modifie des données refuse le GET (405).
    assert client.get(f"/taches/{tache.pk}/faite/").status_code == 405
    reponse = client.post(f"/taches/{tache.pk}/faite/", {"retour": "relances"})
    assert reponse.status_code == 302
    assert reponse.url == "/relances/"
    tache.refresh_from_db()
    assert tache.statut == Tache.Statut.FAITE


@pytest.mark.django_db
def test_autre_commercial_ne_peut_pas_cloturer(client, baobab):
    awa = compte("commercial1@exemple.com")
    tache = Tache.objects.create(
        prospect=baobab, responsable=awa, type="relance", echeance=dans(days=1)
    )
    se_connecter(client, "commercial2@exemple.com")
    reponse = client.post(f"/taches/{tache.pk}/faite/")
    assert reponse.status_code in (403, 404)
    tache.refresh_from_db()
    assert tache.statut == Tache.Statut.A_FAIRE


@pytest.mark.django_db
def test_mes_relances_ne_montre_que_mes_taches_et_les_retards(client, baobab):
    awa, fatou = compte("commercial1@exemple.com"), compte("commercial3@exemple.com")
    Tache.objects.create(
        prospect=baobab, responsable=awa, type="relance", echeance=il_y_a(hours=3)
    )
    ailleurs = Prospect.objects.create(
        nom="Pharmacie du Port", produit=baobab.produit, commercial=fatou, equipe=fatou.equipe
    )
    Tache.objects.create(
        prospect=ailleurs, responsable=fatou, type="rdv", echeance=dans(days=1)
    )
    se_connecter(client, "commercial1@exemple.com")
    contenu = client.get("/relances/").content.decode()
    assert "Garage Baobab" in contenu
    assert "En retard" in contenu
    assert "Pharmacie du Port" not in contenu


@pytest.mark.django_db
def test_relances_exigent_la_connexion(client):
    reponse = client.get("/relances/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")


@pytest.mark.django_db
def test_fiche_propose_les_actions_au_commercial(client, baobab):
    se_connecter(client, "commercial1@exemple.com")
    contenu = client.get(f"/prospects/{baobab.pk}/").content.decode()
    assert "Consigner une activité" in contenu
    assert "Planifier une relance" in contenu
