"""Commande « verifier_objectifs » : alerte les responsables des objectifs en écart.

À planifier une fois par jour. Une alerte par objectif et par semaine au plus.
"""
from django.core.management.base import BaseCommand

from applications.notifications.objectifs import verifier_objectifs


class Command(BaseCommand):
    help = "Alerte les responsables commerciaux des objectifs en écart sur la période."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tolerance",
            type=int,
            default=None,
            help="Points d'écart tolérés (par défaut : réglage du projet).",
        )

    def handle(self, *args, **options):
        bilan = verifier_objectifs(tolerance=options["tolerance"])
        self.stdout.write(
            f"{bilan['objectifs_suivis']} objectif(s) en cours ; "
            f"{bilan['en_ecart']} en écart ; {bilan['alertes']} alerte(s) créée(s)."
        )
