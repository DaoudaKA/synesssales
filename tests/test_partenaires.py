"""Tests des partenaires : fiche, statuts et éléments rattachés."""
import pytest

from applications.partenaires.models import (
    Categorie,
    Contact,
    Localisation,
    Partenaire,
    ServicePropose,
)


@pytest.mark.django_db
def test_statuts_par_defaut():
    partenaire = Partenaire.objects.create(nom_commercial="Garage Teranga")
    assert partenaire.statut_verification == Partenaire.StatutVerification.A_VERIFIER
    assert partenaire.statut_commercial == Partenaire.StatutCommercial.NON_CONTACTE
    assert partenaire.date_derniere_verification is None
    assert str(partenaire) == "Garage Teranga"


@pytest.mark.django_db
def test_fiche_complete():
    auto = Categorie.objects.create(nom="Automobile", type="auto")
    mecanique = Categorie.objects.create(nom="Mécanique", categorie_parent=auto)
    partenaire = Partenaire.objects.create(nom_commercial="Garage Teranga", categorie=mecanique)
    Localisation.objects.create(partenaire=partenaire, pays="Sénégal", ville="Dakar")
    Contact.objects.create(
        partenaire=partenaire, type=Contact.Type.TELEPHONE, valeur="+221 77 000 00 00"
    )
    ServicePropose.objects.create(
        partenaire=partenaire, libelle="Vidange", tarif=15000, devise="XOF", unite="intervention"
    )
    assert mecanique in auto.sous_categories.all()
    assert partenaire.localisations.count() == 1
    assert partenaire.contacts.count() == 1
    assert partenaire.services.first().devise == "XOF"
    assert str(partenaire.localisations.first()) == "Dakar, Sénégal"


@pytest.mark.django_db
def test_informations_manquantes_restent_vides():
    partenaire = Partenaire.objects.create(nom_commercial="Sans détails")
    localisation = Localisation.objects.create(partenaire=partenaire, pays="Sénégal")
    service = ServicePropose.objects.create(partenaire=partenaire, libelle="Diagnostic")
    assert localisation.latitude is None
    assert service.tarif is None


@pytest.mark.django_db
def test_suppression_partenaire_supprime_ses_elements():
    partenaire = Partenaire.objects.create(nom_commercial="À supprimer")
    Contact.objects.create(partenaire=partenaire, type="email", valeur="a@exemple.com")
    partenaire.delete()
    assert Contact.objects.count() == 0


@pytest.mark.django_db
def test_suppression_categorie_conserve_les_partenaires():
    categorie = Categorie.objects.create(nom="Assurance")
    partenaire = Partenaire.objects.create(nom_commercial="Assur+", categorie=categorie)
    categorie.delete()
    partenaire.refresh_from_db()
    assert partenaire.categorie is None
