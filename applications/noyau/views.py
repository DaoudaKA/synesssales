"""Vues communes du projet."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from applications.comptes.permissions import a_le_droit, peut_consulter


def sante(request):
    """Indique que l'application tourne."""
    return JsonResponse({"statut": "ok"})


@login_required
def accueil(request):
    """Page d'accueil : qui est connecté, avec quels rôles."""
    contexte = {
        "roles": request.user.roles.all(),
        "peut_voir_prospects": a_le_droit(request.user, "Prospects", "L"),
        "peut_voir_affectations": a_le_droit(request.user, "Équipes et affectations", "L"),
        "peut_voir_partenaires": peut_consulter(request.user, "Fiches partenaires"),
    }
    return render(request, "noyau/accueil.html", contexte)
