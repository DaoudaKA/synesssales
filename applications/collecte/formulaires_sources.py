"""Formulaires du registre des sources de données."""
from django import forms

from .connecteurs import CONNECTEURS
from .models import SourceDonnees


class SourceForm(forms.ModelForm):
    """Création d'une source. Elle naît toujours « non autorisée »."""

    code_connecteur = forms.ChoiceField(required=False, label="Connecteur", choices=[])

    class Meta:
        model = SourceDonnees
        fields = ["nom", "type", "url", "code_connecteur"]
        labels = {
            "nom": "Nom de la source",
            "type": "Type (site public, fichier, API...)",
            "url": "Adresse (facultative)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Les connecteurs proposés sont ceux du registre : pas de code inventé.
        self.fields["code_connecteur"].choices = [("", "Aucun (import de fichier)")] + [
            (code, code) for code in sorted(CONNECTEURS)
        ]


class ReferenceValidationForm(forms.Form):
    """Référence du document par lequel SYNESS valide la source."""

    reference = forms.CharField(max_length=200)


class RevocationForm(forms.Form):
    """Motif obligatoire pour retirer l'autorisation d'une source."""

    motif = forms.CharField(max_length=300)
