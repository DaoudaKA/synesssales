"""Vues du pilotage commercial."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from applications.comptes.permissions import a_le_droit

from .models import Affectation, Prospect


@login_required
def liste_prospects(request):
    """Liste des prospects visibles avec les droits de la personne connectée."""
    if not a_le_droit(request.user, "Prospects", "L"):
        raise PermissionDenied
    prospects = Prospect.objects.visible_to(request.user).select_related(
        "produit", "commercial", "equipe"
    )
    return render(request, "ventes/prospects.html", {"prospects": prospects})



@login_required
def liste_affectations(request):
    """Affectations visibles avec les droits de la personne connectée."""
    if not a_le_droit(request.user, "Équipes et affectations", "L"):
        raise PermissionDenied
    affectations = Affectation.objects.visible_to(request.user).select_related(
        "utilisateur", "produit", "campagne"
    )
    return render(request, "ventes/affectations.html", {"affectations": affectations})
