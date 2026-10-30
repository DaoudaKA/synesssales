"""Vues communes du projet."""
from django.http import JsonResponse


def sante(request):
    """Indique que l'application tourne."""
    return JsonResponse({"statut": "ok"})
