"""Écrans du registre des sources de données (cahier, Jalon 3)."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from applications.comptes.permissions import a_le_droit, peut_consulter
from applications.comptes.services import journaliser

from .formulaires_sources import ReferenceValidationForm, RevocationForm, SourceForm
from .models import SourceDonnees
from .services import revoquer_source, valider_source

RESSOURCE = "Collectes et imports"


@login_required
def liste_sources(request):
    """Registre des sources : consultation (L, C ou M), actions selon les droits."""
    if not peut_consulter(request.user, RESSOURCE):
        raise PermissionDenied
    contexte = {
        "sources": SourceDonnees.objects.select_related("validee_par"),
        "peut_creer": a_le_droit(request.user, RESSOURCE, "C"),
        "peut_valider": a_le_droit(request.user, RESSOURCE, "M"),
        "erreur": request.GET.get("erreur", ""),
    }
    return render(request, "collecte/sources.html", contexte)


@login_required
def nouvelle_source(request):
    """Crée une source. Elle reste « non autorisée » jusqu'à la validation de SYNESS."""
    if not a_le_droit(request.user, RESSOURCE, "C"):
        raise PermissionDenied
    formulaire = SourceForm(request.POST or None)
    if request.method == "POST" and formulaire.is_valid():
        source = formulaire.save()
        journaliser(
            request.user,
            "creation",
            RESSOURCE,
            source.pk,
            f"Source « {source.nom} » créée (non autorisée)",
        )
        return redirect("sources")
    return render(request, "collecte/source_formulaire.html", {"formulaire": formulaire})


@login_required
@require_POST
def validation_source(request, pk):
    """Enregistre la validation de SYNESS (droit M), avec la référence du document."""
    if not a_le_droit(request.user, RESSOURCE, "M"):
        raise PermissionDenied
    source = get_object_or_404(SourceDonnees, pk=pk)
    formulaire = ReferenceValidationForm(request.POST)
    if not formulaire.is_valid():
        return redirect(f"{reverse('sources')}?erreur=reference")
    valider_source(source, request.user, formulaire.cleaned_data["reference"])
    journaliser(
        request.user,
        "validation",
        RESSOURCE,
        source.pk,
        f"Source « {source.nom} » autorisée. Référence : {source.reference_validation}",
    )
    return redirect("sources")


@login_required
@require_POST
def revocation_source(request, pk):
    """Retire l'autorisation d'une source (droit M), avec un motif obligatoire."""
    if not a_le_droit(request.user, RESSOURCE, "M"):
        raise PermissionDenied
    source = get_object_or_404(SourceDonnees, pk=pk)
    formulaire = RevocationForm(request.POST)
    if not formulaire.is_valid():
        return redirect(f"{reverse('sources')}?erreur=motif")
    revoquer_source(source, formulaire.cleaned_data["motif"])
    journaliser(
        request.user,
        "modification",
        RESSOURCE,
        source.pk,
        f"Autorisation de « {source.nom} » retirée. Motif : {formulaire.cleaned_data['motif']}",
    )
    return redirect("sources")
