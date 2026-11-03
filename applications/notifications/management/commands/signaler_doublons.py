"""Commande « signaler_doublons » : prévient le responsable data des doublons en attente.

À planifier une fois par jour. Sans changement, aucun message n'est répété.
"""
from django.core.management.base import BaseCommand

from applications.notifications.doublons import signaler_doublons


class Command(BaseCommand):
    help = "Signale au responsable data les doublons de fiches partenaires à traiter."

    def handle(self, *args, **options):
        bilan = signaler_doublons()
        self.stdout.write(
            f"{bilan['ouvertes']} doublon(s) en attente ; "
            f"{bilan['alertes']} message(s) créé(s)."
        )
