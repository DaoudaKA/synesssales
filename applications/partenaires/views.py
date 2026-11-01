"""Écrans de la collecte : fiches partenaires."""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse

from applications.comptes.permissions import a_le_droit, peut_consulter
from applications.comptes.services import journaliser

from .formulaires import PartenaireForm
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
        "peut_creer": a_le_droit(request.user, "Fiches partenaires", "C"),
    }
    return render(request, "partenaires/liste.html", contexte)



@login_required
def nouveau_partenaire(request):
    """Saisie d'une fiche : réservée au droit de création de la matrice."""
    if not a_le_droit(request.user, "Fiches partenaires", "C"):
        raise PermissionDenied
    formulaire = PartenaireForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        partenaire = formulaire.enregistrer()
        journaliser(
            request.user,
            "creation",
            "Fiches partenaires",
            partenaire.pk,
            f"Création de la fiche « {partenaire.nom_commercial} »",
        )
        return redirect(f"{reverse('partenaires')}?{urlencode({'q': partenaire.nom_commercial})}")
    return render(request, "partenaires/formulaire.html", {"formulaire": formulaire})
