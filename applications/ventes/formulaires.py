"""Formulaires du pilotage commercial."""
from django import forms


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
