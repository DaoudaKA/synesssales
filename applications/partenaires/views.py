"""Écrans de la collecte : fiches partenaires."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from applications.comptes.permissions import peut_consulter

from .models import Partenaire


@login_required
def liste_partenaires(request):
    """Liste des fiches visibles, avec recherche et filtre de vérification."""
    if not peut_consulter(request.user, "Fiches partenaires"):
        raise PermissionDenied
    terme = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    partenaires = (
        Partenaire.objects.visible_to(request.user)
        .rechercher(terme)
        .select_related("categorie")
        .prefetch_related("localisations")
    )
    if statut in Partenaire.StatutVerification.values:
        partenaires = partenaires.filter(statut_verification=statut)
    contexte = {
        "partenaires": partenaires,
        "terme": terme,
        "statut": statut,
        "statuts": Partenaire.StatutVerification.choices,
    }
    return render(request, "partenaires/liste.html", contexte)
