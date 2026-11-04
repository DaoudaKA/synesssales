"""Formulaires du registre des sources de données."""
from django import forms

from .models import SourceDonnees


class SourceForm(forms.ModelForm):
    """Création d'une source. Elle naît toujours « non autorisée »."""

    class Meta:
        model = SourceDonnees
        fields = ["nom", "type", "url"]
        labels = {
            "nom": "Nom de la source",
            "type": "Type (site public, fichier, API...)",
            "url": "Adresse (facultative)",
        }


class ReferenceValidationForm(forms.Form):
    """Référence du document par lequel SYNESS valide la source."""

    reference = forms.CharField(max_length=200)


class RevocationForm(forms.Form):
    """Motif obligatoire pour retirer l'autorisation d'une source."""

    motif = forms.CharField(max_length=300)
