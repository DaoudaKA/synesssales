"""Vues communes du projet."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from applications.comptes.permissions import a_le_droit


def sante(request):
    """Indique que l'application tourne."""
    return JsonResponse({"statut": "ok"})


@login_required
def accueil(request):
    """Page d'accueil : qui est connecté, avec quels rôles."""
    contexte = {
        "roles": request.user.roles.all(),
        "peut_voir_prospects": a_le_droit(request.user, "Prospects", "L"),
    }
    return render(request, "noyau/accueil.html", contexte)
