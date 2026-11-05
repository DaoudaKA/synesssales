"""Rapport de qualité d'une collecte : compteurs, taux de rejet et lignes rejetées."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from applications.comptes.permissions import peut_consulter

from .models import Collecte

RESSOURCE = "Collectes et imports"
# Au-delà, le détail des rejets est tronqué à l'écran (le journal complet reste en base).
MAX_REJETS_AFFICHES = 200


@login_required
def rapport_collecte(request, pk):
    """Rapport d'une collecte : réservé à ceux qui peuvent consulter les collectes."""
    if not peut_consulter(request.user, RESSOURCE):
        raise PermissionDenied
    collecte = get_object_or_404(Collecte.objects.select_related("source"), pk=pk)

    # Taux de rejet = lignes refusées / lignes traitées (fiches créées + lignes refusées).
    traitees = collecte.nb_fiches + collecte.nb_erreurs
    taux_rejet = round(100 * collecte.nb_erreurs / traitees) if traitees else 0
    duree = None
    if collecte.date_fin:
        duree = int((collecte.date_fin - collecte.date_debut).total_seconds())

    rejets = collecte.rejets.all()
    contexte = {
        "collecte": collecte,
        "lignes_traitees": traitees,
        "taux_rejet": taux_rejet,
        "duree_secondes": duree,
        "rejets": rejets[:MAX_REJETS_AFFICHES],
        "rejets_tronques": rejets.count() > MAX_REJETS_AFFICHES,
    }
    return render(request, "collecte/rapport.html", contexte)
