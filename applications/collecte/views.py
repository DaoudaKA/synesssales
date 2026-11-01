"""Écrans de la collecte : liste des collectes et import CSV."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from applications.comptes.permissions import a_le_droit, peut_consulter
from applications.comptes.services import journaliser

from .formulaires import ImportCsvForm
from .models import Collecte
from .services import ImportInvalide, importer_csv


@login_required
def liste_collectes(request):
    """Historique des collectes (droit de consultation de la matrice)."""
    if not peut_consulter(request.user, "Collectes et imports"):
        raise PermissionDenied
    contexte = {
        "collectes": Collecte.objects.select_related("source"),
        "peut_importer": a_le_droit(request.user, "Collectes et imports", "C"),
    }
    return render(request, "collecte/liste.html", contexte)



@login_required
def importer(request):
    """Import d'un fichier CSV : réservé au droit de création de la matrice."""
    if not a_le_droit(request.user, "Collectes et imports", "C"):
        raise PermissionDenied
    formulaire = ImportCsvForm(request.POST or None, request.FILES or None)
    resultat = None
    if request.method == "POST" and formulaire.is_valid():
        try:
            collecte, erreurs = importer_csv(
                formulaire.cleaned_data["fichier"].read(), formulaire.cleaned_data["source"]
            )
        except ImportInvalide as erreur:
            # Fichier illisible : on affiche le motif sur le formulaire.
            formulaire.add_error("fichier", str(erreur))
        else:
            journaliser(
                request.user,
                "import",
                "Collectes et imports",
                collecte.pk,
                f"{collecte.nb_fiches} fiche(s) importée(s), {collecte.nb_erreurs} erreur(s) "
                f"depuis « {collecte.source} »",
            )
            resultat = {"collecte": collecte, "erreurs": erreurs}
    # Ces deux lignes sont HORS du bloc « if » : elles servent dans tous les cas
    # (première visite, formulaire refusé, import réussi).
    contexte = {"formulaire": formulaire, "resultat": resultat}
    return render(request, "collecte/importer.html", contexte)
