"""Écrans du pilotage commercial."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from applications.comptes.permissions import a_le_droit, portees
from applications.comptes.services import journaliser

from .formulaires import ReaffectationForm
from .models import Affectation, Prospect
from .services import commerciaux_cibles, reaffecter_prospect


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



def _peut_reaffecter(utilisateur):
    """Réaffecter demande le droit de modifier, hors portée « propre »."""
    return bool(portees(utilisateur, "Prospects", "M") & {"toute", "perimetre"})


@login_required
def fiche_prospect(request, pk):
    """Fiche d'un prospect : informations, historique et réaffectation."""
    if not a_le_droit(request.user, "Prospects", "L"):
        raise PermissionDenied
    # Même filtre que la liste : un prospect hors périmètre est introuvable (404).
    visibles = Prospect.objects.visible_to(request.user).select_related(
        "produit", "commercial", "equipe", "partenaire"
    )
    prospect = get_object_or_404(visibles, pk=pk)

    formulaire = None
    if _peut_reaffecter(request.user):
        formulaire = ReaffectationForm(
            request.POST or None,
            commerciaux=commerciaux_cibles(request.user),
            prospect=prospect,
        )
        if request.method == "POST" and formulaire.is_valid():
            ancien = prospect.commercial
            nouveau = formulaire.cleaned_data["commercial"]
            reaffecter_prospect(
                prospect, nouveau, request.user, formulaire.cleaned_data["motif"]
            )
            journaliser(
                request.user,
                "reaffectation",
                "Prospects",
                prospect.pk,
                f"« {prospect.nom} » : {ancien or 'aucun commercial'} → {nouveau}",
            )
            return redirect("prospect", pk=prospect.pk)
    elif request.method == "POST":
        # Sans le droit de réaffecter, aucune modification n'est acceptée.
        raise PermissionDenied

    contexte = {
        "prospect": prospect,
        "formulaire": formulaire,
        "reaffectations": prospect.reaffectations.select_related(
            "ancien_commercial", "nouveau_commercial", "auteur"
        ),
        "activites": prospect.activites.select_related("auteur")[:10],
        "taches": prospect.taches.filter(statut="a_faire").select_related("responsable"),
    }
    return render(request, "ventes/prospect.html", contexte)
