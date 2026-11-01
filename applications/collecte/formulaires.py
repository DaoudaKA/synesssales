"""Formulaire d'import d'un fichier CSV."""
from django import forms

from .models import SourceDonnees

TAILLE_MAX = 2 * 1024 * 1024  # 2 Mo


class ImportCsvForm(forms.Form):
    # Seules les sources aux conditions d'usage validées sont proposées.
    source = forms.ModelChoiceField(
        label="Source des données",
        queryset=SourceDonnees.objects.filter(conditions_validees=True),
    )
    fichier = forms.FileField(label="Fichier CSV")

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        if not fichier.name.lower().endswith(".csv"):
            raise forms.ValidationError("Le fichier doit avoir l'extension .csv.")
        if fichier.size > TAILLE_MAX:
            raise forms.ValidationError("Le fichier dépasse 2 Mo.")
        return fichier
