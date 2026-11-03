"""Commande « envoyer_courriels » : envoie les e-mails de notification en attente.

À planifier à intervalle court (par exemple toutes les 5 minutes).
"""
from django.core.management.base import BaseCommand

from applications.notifications.courriels import envoyer_courriels


class Command(BaseCommand):
    help = "Envoie par e-mail les notifications en attente (avec nouvelles tentatives)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--plafond",
            type=int,
            default=None,
            help="Nombre maximum d'e-mails pour cette exécution (par défaut : réglage).",
        )

    def handle(self, *args, **options):
        bilan = envoyer_courriels(plafond=options["plafond"])
        self.stdout.write(
            f"{bilan['envoyes']} e-mail(s) envoyé(s) ; {bilan['echecs']} échec(s) ; "
            f"{bilan['restants']} en attente du prochain passage."
        )
