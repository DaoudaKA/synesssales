"""Formulaire de saisie d'une fiche partenaire."""
from django import forms
from django.db import transaction

from .models import Contact, Localisation, Partenaire, ServicePropose


class PartenaireForm(forms.ModelForm):
    """Fiche partenaire avec sa première localisation, ses contacts et un service."""

    pays = forms.CharField(label="Pays", max_length=80, initial="Sénégal")
    region = forms.CharField(label="Région", max_length=80, required=False)
    ville = forms.CharField(label="Ville", max_length=80, required=False)
    adresse = forms.CharField(label="Adresse", max_length=255, required=False)
    telephone = forms.CharField(label="Téléphone", max_length=255, required=False)
    email = forms.EmailField(label="E-mail", max_length=255, required=False)
    service = forms.CharField(label="Service proposé", max_length=200, required=False)

    class Meta:
        model = Partenaire
        fields = ["nom_commercial", "raison_sociale", "categorie", "description"]

    @transaction.atomic
    def enregistrer(self):
        """Crée la fiche et ses éléments liés. Retourne le partenaire."""
        donnees = self.cleaned_data
        partenaire = self.save()
        Localisation.objects.create(
            partenaire=partenaire,
            pays=donnees["pays"],
            region=donnees["region"],
            ville=donnees["ville"],
            adresse=donnees["adresse"],
        )
        if donnees["telephone"]:
            Contact.objects.create(
                partenaire=partenaire, type=Contact.Type.TELEPHONE, valeur=donnees["telephone"]
            )
        if donnees["email"]:
            Contact.objects.create(
                partenaire=partenaire, type=Contact.Type.EMAIL, valeur=donnees["email"]
            )
        if donnees["service"]:
            ServicePropose.objects.create(partenaire=partenaire, libelle=donnees["service"])
        return partenaire
