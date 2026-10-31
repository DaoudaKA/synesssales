"""Vues communes du projet."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render


def sante(request):
    """Indique que l'application tourne."""
    return JsonResponse({"statut": "ok"})


@login_required
def accueil(request):
    """Page d'accueil : qui est connecté, avec quels rôles."""
    return render(request, "noyau/accueil.html", {"roles": request.user.roles.all()})
