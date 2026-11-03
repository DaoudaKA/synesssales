"""Signalement regroupé des doublons de fiches partenaires en attente."""
from django.utils import timezone

from applications.collecte.models import AlerteDoublon

from . import evenements


def signaler_doublons(aujourdhui=None):
    """Prévient les responsables data qu'il reste des doublons à traiter.

    Un seul message regroupe toutes les alertes ouvertes. Aucun message s'il n'y en a pas.
    Retourne un bilan chiffré.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    nombre = AlerteDoublon.objects.filter(statut=AlerteDoublon.Statut.OUVERTE).count()

    bilan = {"ouvertes": nombre, "alertes": 0}
    if nombre == 0:
        return bilan
    for destinataire in evenements.responsables_data():
        if evenements.doublons_a_traiter(destinataire, nombre, aujourdhui):
            bilan["alertes"] += 1
    return bilan
