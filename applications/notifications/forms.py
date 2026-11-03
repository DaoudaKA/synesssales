"""Formulaire de paramétrage des notifications."""
from django import forms

from applications.comptes.services import journaliser

from .models import Parametre
from .parametres import PARAMETRES, valeur

RESSOURCE = "Notifications (paramétrage)"


class ParametresForm(forms.Form):
    """Un champ numérique par paramètre du catalogue, borné par ses limites."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for cle, definition in PARAMETRES.items():
            self.fields[cle] = forms.IntegerField(
                label=definition["libelle"],
                min_value=definition["min"],
                max_value=definition["max"],
                initial=valeur(cle),
                help_text=(
                    f"En {definition['unite']} "
                    f"(de {definition['min']} à {definition['max']}). "
                    f"Valeur par défaut : {definition['defaut']}."
                ),
            )

    def enregistrer(self, utilisateur):
        """Enregistre les valeurs changées et journalise chaque modification.

        Retourne la liste des clés modifiées.
        """
        modifiees = []
        for cle in PARAMETRES:
            nouvelle = self.cleaned_data[cle]
            ancienne = valeur(cle)
            if nouvelle == ancienne:
                continue
            parametre, _ = Parametre.objects.update_or_create(
                cle=cle, defaults={"valeur": nouvelle, "modifie_par": utilisateur}
            )
            journaliser(
                utilisateur,
                "modification",
                RESSOURCE,
                parametre.pk,
                f"{cle} : {ancienne} → {nouvelle}",
            )
            modifiees.append(cle)
        return modifiees
