"""Formulaires du pilotage commercial."""
import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Activite, Contrat, Objectif, Tache

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



class ContratForm(forms.ModelForm):
    """Soumission d'un contrat à validation."""

    class Meta:
        model = Contrat
        fields = ["date_signature"]
        labels = {"date_signature": "Date de signature"}
        widgets = {
            "date_signature": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }

    def __init__(self, *args, prospect, **kwargs):
        super().__init__(*args, **kwargs)
        self.prospect = prospect
        # Le modèle accepte une date vide, mais pas la soumission d'un contrat.
        self.fields["date_signature"].required = True

    def clean_date_signature(self):
        valeur = self.cleaned_data["date_signature"]
        if valeur > timezone.localdate():
            raise forms.ValidationError("La date de signature ne peut pas être dans le futur.")
        return valeur

    def clean(self):
        donnees = super().clean()
        en_cours = [Contrat.StatutValidation.SOUMIS, Contrat.StatutValidation.VALIDE]
        # Un contrat refusé n'empêche pas d'en soumettre un nouveau.
        if self.prospect.contrats.filter(statut_validation__in=en_cours).exists():
            raise forms.ValidationError(
                "Un contrat est déjà soumis ou validé pour ce prospect."
            )
        return donnees


class RefusForm(forms.Form):
    """Motif obligatoire pour refuser un contrat."""

    motif = forms.CharField(
        label="Motif du refus", widget=forms.Textarea(attrs={"rows": 3})
    )




class ObjectifForm(forms.ModelForm):
    """Création et modification d'un objectif individuel ou collectif."""

    cible = forms.IntegerField(label="Cible (contrats validés)", min_value=1)

    class Meta:
        model = Objectif
        fields = ["produit", "equipe", "commercial", "cible", "date_debut", "date_fin"]
        labels = {
            "commercial": "Commercial (vide = objectif collectif de l'équipe)",
            "date_debut": "Début de la période",
            "date_fin": "Fin de la période",
        }
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        commerciaux = get_user_model().objects.filter(statut="actif", roles__nom="Commercial")
        self.fields["commercial"].queryset = commerciaux.distinct()
        self.fields["commercial"].required = False

    def clean(self):
        donnees = super().clean()
        equipe = donnees.get("equipe")
        commercial = donnees.get("commercial")
        produit = donnees.get("produit")
        debut = donnees.get("date_debut")
        fin = donnees.get("date_fin")
        if debut and fin and fin < debut:
            raise forms.ValidationError("La fin de la période doit suivre son début.")
        # Un objectif individuel doit porter sur quelqu'un de l'équipe choisie.
        if commercial and equipe and commercial.equipe_id != equipe.pk:
            raise forms.ValidationError("Ce commercial n'appartient pas à cette équipe.")
        if produit and equipe and debut and fin:
            # Même porteur, même produit : deux périodes ne doivent pas se chevaucher.
            # filter(commercial=None) cherche les objectifs collectifs (colonne vide).
            chevauchements = Objectif.objects.filter(
                produit=produit,
                equipe=equipe,
                commercial=commercial,
                date_debut__lte=fin,
                date_fin__gte=debut,
            )
            if self.instance.pk:
                chevauchements = chevauchements.exclude(pk=self.instance.pk)
            if chevauchements.exists():
                raise forms.ValidationError(
                    "Un objectif existe déjà pour ce porteur, ce produit et cette période."
                )
        return donnees
