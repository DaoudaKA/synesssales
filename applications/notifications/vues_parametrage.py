"""Écran de paramétrage des notifications (cahier, section 9.2)."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse

from applications.comptes.permissions import a_le_droit, peut_consulter

from .forms import RESSOURCE, ParametresForm


@login_required
def parametrage(request):
    """Affiche et enregistre les seuils. Lecture : droit L, C ou M ; écriture : droit M."""
    if not peut_consulter(request.user, RESSOURCE):
        raise PermissionDenied
    peut_modifier = a_le_droit(request.user, RESSOURCE, "M")

    if request.method == "POST":
        if not peut_modifier:
            raise PermissionDenied
        formulaire = ParametresForm(request.POST)
        if formulaire.is_valid():
            modifiees = formulaire.enregistrer(request.user)
            adresse = reverse("parametrage_notifications")
            return redirect(f"{adresse}?ok={len(modifiees)}")
    else:
        formulaire = ParametresForm()

    # Sans droit de modification, l'écran reste consultable mais en lecture seule.
    if not peut_modifier:
        for champ in formulaire.fields.values():
            champ.disabled = True

    ok = request.GET.get("ok", "")
    contexte = {
        "formulaire": formulaire,
        "peut_modifier": peut_modifier,
        "enregistres": ok if ok.isdigit() else None,
    }
    return render(request, "notifications/parametrage.html", contexte)
