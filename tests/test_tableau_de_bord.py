"""Tests du tableau de bord commercial : portées, chiffres clés, résultats comparés."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from applications.comptes.models import Role
from applications.ventes.models import Contrat, Prospect, Tache
from applications.ventes.tableau_de_bord import (
    indicateurs,
    prospects_du_tableau,
    ventilation,
)

Utilisateur = get_user_model()
MOT_DE_PASSE = "motdepasse-de-test-123"
ADRESSE = "/tableau-de-bord/"


@pytest.fixture
def demo(db):
    call_command("charger_demo", "--mot-de-passe", MOT_DE_PASSE)


@pytest.fixture
def awa(demo):
    return Utilisateur.objects.get(email="commercial1@exemple.com")


@pytest.fixture
def baobab(demo):
    return Prospect.objects.get(nom="Garage Baobab")


def utilisateur_avec_role(email, role):
    personne = Utilisateur.objects.create(email=email, nom=email)
    personne.roles.add(Role.objects.get(nom=role))
    return personne


@pytest.fixture
def responsable(demo):
    return utilisateur_avec_role("responsable@exemple.com", "Responsable commercial")


@pytest.mark.django_db
def test_visiteur_anonyme_est_renvoye_vers_la_connexion(client, demo):
    assert client.get(ADRESSE).status_code == 302


@pytest.mark.django_db
def test_administrateur_systeme_n_a_pas_acces(client, demo):
    admin = utilisateur_avec_role("admin-test@exemple.com", "Administrateur système")
    client.force_login(admin)
    assert client.get(ADRESSE).status_code == 403


@pytest.mark.django_db
def test_commercial_ne_voit_que_ses_prospects(client, awa):
    client.force_login(awa)
    reponse = client.get(ADRESSE)
    assert reponse.status_code == 200
    attendu = Prospect.objects.filter(commercial=awa).count()
    assert reponse.context["indicateurs"]["total"] == attendu
    assert attendu < Prospect.objects.count()


@pytest.mark.django_db
def test_chef_d_equipe_voit_son_equipe(awa):
    chef = awa.equipe.chef_equipe
    attendu = Prospect.objects.filter(equipe__chef_equipe=chef).count()
    assert prospects_du_tableau(chef).count() == attendu
    assert attendu < Prospect.objects.count()


@pytest.mark.django_db
def test_responsable_commercial_voit_tout(responsable):
    assert prospects_du_tableau(responsable).count() == Prospect.objects.count()


@pytest.mark.django_db
def test_taux_de_conversion(responsable, baobab):
    baobab.statut = Prospect.Statut.GAGNE
    baobab.save()
    resultat = indicateurs(prospects_du_tableau(responsable), responsable)
    total = Prospect.objects.count()
    gagnes = Prospect.objects.filter(statut=Prospect.Statut.GAGNE).count()
    assert resultat["gagnes"] == gagnes >= 1
    assert resultat["taux_conversion"] == round(100 * gagnes / total)
    # Tous les statuts sont listés, et leur somme redonne le total.
    assert sum(ligne["total"] for ligne in resultat["par_statut"]) == total


@pytest.mark.django_db
def test_ventilations_redonnent_le_total(responsable):
    prospects = prospects_du_tableau(responsable)
    total = prospects.count()
    for champ in ("equipe__nom", "produit__nom", "campagne__nom", "campagne__zone"):
        assert sum(ligne["total"] for ligne in ventilation(prospects, champ)) == total


@pytest.mark.django_db
def test_prospect_sans_campagne_est_classe_non_renseigne(responsable, baobab):
    Prospect.objects.filter(pk=baobab.pk).update(campagne=None)
    libelles = [
        ligne["libelle"]
        for ligne in ventilation(prospects_du_tableau(responsable), "campagne__nom")
    ]
    assert "Non renseigné" in libelles


@pytest.mark.django_db
def test_relances_en_retard_limitees_a_la_portee(awa, baobab):
    Tache.objects.create(
        prospect=baobab,
        responsable=awa,
        type="relance",
        echeance=timezone.now() - datetime.timedelta(hours=3),
    )
    fatou = Utilisateur.objects.get(email="commercial3@exemple.com")
    assert indicateurs(prospects_du_tableau(awa), awa)["relances_en_retard"] == 1
    # Une commerciale d'une autre équipe ne voit pas ce retard.
    assert indicateurs(prospects_du_tableau(fatou), fatou)["relances_en_retard"] == 0


@pytest.mark.django_db
def test_contrats_a_valider_reserves_aux_validateurs(responsable, awa, baobab):
    Contrat.objects.create(prospect=baobab, date_signature=timezone.localdate())
    assert indicateurs(prospects_du_tableau(responsable), responsable)[
        "contrats_a_valider"
    ] == 1
    # Un commercial n'a pas le droit V : l'indicateur n'est pas affiché (None).
    assert indicateurs(prospects_du_tableau(awa), awa)["contrats_a_valider"] is None


@pytest.mark.django_db
def test_page_affiche_les_blocs(client, responsable):
    client.force_login(responsable)
    contenu = client.get(ADRESSE).content.decode()
    for titre in ("Taux de conversion", "Par équipe", "Par produit", "Par zone"):
        assert titre in contenu
