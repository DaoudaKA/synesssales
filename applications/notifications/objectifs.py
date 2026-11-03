"""Détection des objectifs en écart par rapport à la période écoulée."""
from django.conf import settings
from django.utils import timezone

from applications.ventes.models import Objectif
from applications.ventes.services import avancement

from . import evenements


def verifier_objectifs(aujourdhui=None, tolerance=None):
    """Alerte les responsables des objectifs en cours qui prennent du retard.

    Part de période écoulée (attendu) = jours écoulés / durée totale. Un objectif est
    en écart si son taux d'atteinte est inférieur à l'attendu de `tolerance` points ou plus.
    Retourne un bilan chiffré.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    if tolerance is None:
        tolerance = getattr(settings, "TOLERANCE_ECART_OBJECTIF_POINTS", 20)

    # Seuls les objectifs en cours sont suivis (ni à venir, ni terminés).
    objectifs = Objectif.objects.filter(
        date_debut__lte=aujourdhui, date_fin__gte=aujourdhui
    ).select_related("produit", "equipe", "commercial")
    destinataires = evenements.responsables_objectifs()

    bilan = {"objectifs_suivis": 0, "en_ecart": 0, "alertes": 0}
    for objectif in objectifs:
        bilan["objectifs_suivis"] += 1
        realise, taux = avancement(objectif)
        duree = (objectif.date_fin - objectif.date_debut).days + 1
        ecoule = (aujourdhui - objectif.date_debut).days + 1
        attendu = round(100 * ecoule / duree)
        if attendu - taux < tolerance:
            continue
        bilan["en_ecart"] += 1
        for destinataire in destinataires:
            if evenements.objectif_en_ecart(
                destinataire, objectif, realise, taux, attendu, aujourdhui
            ):
                bilan["alertes"] += 1
    return bilan
