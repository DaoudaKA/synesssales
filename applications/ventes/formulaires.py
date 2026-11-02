"""Formulaires du pilotage commercial."""
import datetime

from django import forms
from django.utils import timezone

from .models import Activite, Tache

# Format du champ HTML « datetime-local » (le navigateur envoie « 2026-11-05T10:30 »).
FORMAT_SAISIE = "%Y-%m-%dT%H:%M"
# Marge pour éviter de refuser une saisie « maintenant » à cause de quelques secondes.
TOLERANCE = datetime.timedelta(minutes=5)


def _champ_date(libelle):
    """Champ date et heure avec le sélecteur natif du navigateur."""
    return forms.DateTimeField(
        label=libelle,
        input_formats=[FORMAT_SAISIE, "%Y-%m-%d %H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=FORMAT_SAISIE),
    )


class ReaffectationForm(forms.Form):
    """Choix du nouveau commercial et du motif."""

    commercial = forms.ModelChoiceField(label="Nouveau commercial", queryset=None)
    motif = forms.CharField(
        label="Motif", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )

    def __init__(self, *args, commerciaux, prospect, **kwargs):
        super().__init__(*args, **kwargs)
        # La liste des choix est limitée à ce que le rôle autorise.
        self.fields["commercial"].queryset = commerciaux
        self.prospect = prospect

    def clean_commercial(self):
        commercial = self.cleaned_data["commercial"]
        if commercial == self.prospect.commercial:
            raise forms.ValidationError("Ce prospect est déjà suivi par ce commercial.")
        return commercial


class ActiviteForm(forms.ModelForm):
    """Saisie d'une interaction passée avec un prospect (appel, visite...)."""

    date = _champ_date("Date et heure")

    class Meta:
        model = Activite
        fields = ["type", "date", "duree_minutes", "resultat", "objections"]
        labels = {
            "type": "Type d'activité",
            "duree_minutes": "Durée (minutes)",
            "resultat": "Résultat",
            "objections": "Objections du client",
        }
        widgets = {
            "resultat": forms.Textarea(attrs={"rows": 2}),
            "objections": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.now  # proposée : maintenant

    def clean_date(self):
        valeur = self.cleaned_data["date"]
        # Une activité est un fait passé : on ne l'enregistre pas à l'avance.
        if valeur > timezone.now() + TOLERANCE:
            raise forms.ValidationError("Une activité ne peut pas être datée dans le futur.")
        return valeur


class TacheForm(forms.ModelForm):
    """Planification d'une relance, d'un rendez-vous ou d'un envoi de proposition."""

    echeance = _champ_date("Échéance")

    class Meta:
        model = Tache
        fields = ["type", "echeance"]
        labels = {"type": "Type de tâche"}

    def clean_echeance(self):
        valeur = self.cleaned_data["echeance"]
        # Une tâche à faire est tournée vers l'avenir.
        if valeur < timezone.now() - TOLERANCE:
            raise forms.ValidationError("L'échéance ne peut pas être dans le passé.")
        return valeur
