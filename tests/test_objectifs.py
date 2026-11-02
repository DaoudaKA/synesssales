"""Tests des objectifs individuels et collectifs, et de leur réalisation."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import JournalAudit, Role
from applications.ventes.models import Contrat, Objectif, Prospect
from applications.ventes.services import avancement, realisation

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
    """Un Responsable commercial (« CMS » sur les objectifs, portée « toute »)."""
    utilisateur = Utilisateur.objects.create(
        email="responsable@exemple.com", nom="Responsable Test"
    )
    utilisateur.roles.add(Role.objects.get(nom="Responsable commercial"))
    return utilisateur


def compte(email):
    return Utilisateur.objects.get(email=email)


def se_connecter(client, utilisateur):
    client.force_login(utilisateur)
    return utilisateur


def jour(decalage=0):
    return timezone.localdate() + datetime.timedelta(days=decalage)


def donnees(baobab, commercial="commercial1@exemple.com", **changements):
    """Données de formulaire valides ; « commercial » vide donne un objectif collectif."""
    awa = compte("commercial1@exemple.com")
    valeurs = {
        "produit": baobab.produit.pk,
        "equipe": awa.equipe.pk,
        "commercial": compte(commercial).pk if commercial else "",
        "cible": 4,
        "date_debut": jour(-10).isoformat(),
        "date_fin": jour(20).isoformat(),
    }
    valeurs.update(changements)
    return valeurs


def objectif_individuel(baobab, **champs):
    awa = compte("commercial1@exemple.com")
    valeurs = {
        "produit": baobab.produit,
        "equipe": awa.equipe,
        "commercial": awa,
        "cible": 4,
        "date_debut": jour(-10),
        "date_fin": jour(20),
    }
    valeurs.update(champs)
    return Objectif.objects.create(**valeurs)


def contrat_valide(prospect, date=None):
    return Contrat.objects.create(
        prospect=prospect,
        date_signature=date or jour(),
        statut_validation=Contrat.StatutValidation.VALIDE,
    )


@pytest.mark.django_db
def test_responsable_cree_un_objectif_individuel(client, baobab, responsable):
    se_connecter(client, responsable)
    reponse = client.post("/objectifs/nouveau/", donnees(baobab))
    assert reponse.status_code == 302
    objectif = Objectif.objects.get()
    assert objectif.commercial == compte("commercial1@exemple.com")
    assert objectif.cree_par == responsable
    assert JournalAudit.objects.filter(
        utilisateur=responsable, action="creation", objet_id=str(objectif.pk)
    ).exists()


@pytest.mark.django_db
def test_responsable_cree_un_objectif_collectif(client, baobab, responsable):
    se_connecter(client, responsable)
    reponse = client.post("/objectifs/nouveau/", donnees(baobab, commercial=None))
    assert reponse.status_code == 302
    assert Objectif.objects.get().commercial is None


@pytest.mark.django_db
def test_commercial_hors_equipe_refuse(client, baobab, responsable):
    se_connecter(client, responsable)
    # commercial3 est dans l'équipe de Thiès, pas dans l'équipe choisie (Dakar).
    reponse = client.post(
        "/objectifs/nouveau/", donnees(baobab, commercial="commercial3@exemple.com")
    )
    assert reponse.status_code == 200
    assert not Objectif.objects.exists()


@pytest.mark.django_db
def test_dates_incoherentes_refusees(client, baobab, responsable):
    se_connecter(client, responsable)
    reponse = client.post(
        "/objectifs/nouveau/",
        donnees(baobab, date_debut=jour(5).isoformat(), date_fin=jour(1).isoformat()),
    )
    assert reponse.status_code == 200
    assert not Objectif.objects.exists()


@pytest.mark.django_db
def test_chevauchement_refuse(client, baobab, responsable):
    objectif_individuel(baobab)
    se_connecter(client, responsable)
    reponse = client.post("/objectifs/nouveau/", donnees(baobab, date_debut=jour(0).isoformat()))
    assert reponse.status_code == 200
    assert Objectif.objects.count() == 1


@pytest.mark.django_db
def test_commercial_ne_peut_pas_creer(client, baobab):
    se_connecter(client, compte("commercial1@exemple.com"))
    assert client.post("/objectifs/nouveau/", donnees(baobab)).status_code == 403
    assert not Objectif.objects.exists()


@pytest.mark.django_db
def test_chef_d_equipe_ne_peut_pas_creer(client, baobab):
    se_connecter(client, compte("chef@exemple.com"))
    assert client.post("/objectifs/nouveau/", donnees(baobab)).status_code == 403


@pytest.mark.django_db
def test_responsable_modifie_un_objectif(client, baobab, responsable):
    objectif = objectif_individuel(baobab)
    se_connecter(client, responsable)
    # Même période que l'objectif modifié : il ne doit pas se refuser lui-même.
    reponse = client.post(
        f"/objectifs/{objectif.pk}/modifier/", donnees(baobab, cible=9)
    )
    assert reponse.status_code == 302
    objectif.refresh_from_db()
    assert objectif.cible == 9
    assert JournalAudit.objects.filter(
        utilisateur=responsable, action="modification", objet_id=str(objectif.pk)
    ).exists()


@pytest.mark.django_db
def test_realisation_ne_compte_que_les_contrats_valides_de_la_periode(baobab):
    objectif = objectif_individuel(baobab)
    contrat_valide(baobab)  # compté
    contrat_valide(baobab, date=jour(-40))  # hors période
    Contrat.objects.create(prospect=baobab, date_signature=jour())  # soumis : pas compté
    autre = Prospect.objects.create(
        nom="Pharmacie du Port",
        produit=baobab.produit,
        commercial=compte("commercial2@exemple.com"),
        equipe=compte("commercial2@exemple.com").equipe,
    )
    contrat_valide(autre)  # un autre commercial : pas compté pour l'individuel
    assert realisation(objectif) == 1
    assert avancement(objectif) == (1, 25)  # 1 contrat sur une cible de 4


@pytest.mark.django_db
def test_objectif_collectif_compte_toute_l_equipe(baobab):
    moussa = compte("commercial2@exemple.com")
    collectif = objectif_individuel(baobab, commercial=None)
    contrat_valide(baobab)
    contrat_valide(
        Prospect.objects.create(
            nom="Pharmacie du Port", produit=baobab.produit, commercial=moussa, equipe=moussa.equipe
        )
    )
    assert realisation(collectif) == 2


@pytest.mark.django_db
def test_liste_limitee_a_l_equipe_du_commercial(client, baobab):
    objectif_individuel(baobab)  # équipe de Dakar
    fatou = compte("commercial3@exemple.com")
    Objectif.objects.create(
        produit=baobab.produit,
        equipe=fatou.equipe,
        commercial=fatou,
        cible=7,
        date_debut=jour(-10),
        date_fin=jour(20),
    )
    se_connecter(client, compte("commercial1@exemple.com"))
    contenu = client.get("/objectifs/").content.decode()
    assert compte("commercial1@exemple.com").nom in contenu
    assert fatou.nom not in contenu  # l'objectif de Thiès reste invisible


@pytest.mark.django_db
def test_responsable_voit_tous_les_objectifs(client, baobab, responsable):
    objectif_individuel(baobab)
    fatou = compte("commercial3@exemple.com")
    Objectif.objects.create(
        produit=baobab.produit,
        equipe=fatou.equipe,
        commercial=fatou,
        cible=7,
        date_debut=jour(-10),
        date_fin=jour(20),
    )
    se_connecter(client, responsable)
    contenu = client.get("/objectifs/").content.decode()
    assert compte("commercial1@exemple.com").nom in contenu
    assert fatou.nom in contenu
    assert "Nouvel objectif" in contenu


@pytest.mark.django_db
def test_liste_affiche_le_taux_d_atteinte(client, baobab):
    objectif_individuel(baobab)
    contrat_valide(baobab)
    se_connecter(client, compte("commercial1@exemple.com"))
    contenu = client.get("/objectifs/").content.decode()
    assert "25 %" in contenu
    assert "Nouvel objectif" not in contenu  # un commercial consulte seulement


@pytest.mark.django_db
def test_liste_refusee_au_responsable_data(client, demo):
    se_connecter(client, compte("data@exemple.com"))
    assert client.get("/objectifs/").status_code == 403


@pytest.mark.django_db
def test_liste_exige_la_connexion(client):
    reponse = client.get("/objectifs/")
    assert reponse.status_code == 302
    assert reponse.url.startswith("/connexion/")
