"""Commande « lancer_collecte » : lance la collecte d'une source par son connecteur.

Refuse de démarrer si la source n'est pas autorisée par SYNESS.
"""
from django.core.management.base import BaseCommand, CommandError

from applications.collecte.connecteurs import lancer_collecte
from applications.collecte.models import SourceDonnees
from applications.collecte.services import ImportInvalide


class Command(BaseCommand):
    help = "Lance la collecte d'une source autorisée, avec son connecteur."

    def add_arguments(self, parser):
        parser.add_argument("source", help="Nom exact de la source de données.")

    def handle(self, *args, **options):
        try:
            source = SourceDonnees.objects.get(nom=options["source"])
        except SourceDonnees.DoesNotExist as erreur:
            raise CommandError(f"Source inconnue : « {options['source']} ».") from erreur
        try:
            collecte, erreurs = lancer_collecte(source)
        except ImportInvalide as erreur:
            raise CommandError(str(erreur)) from erreur
        self.stdout.write(
            f"Collecte {collecte.pk} : {collecte.get_statut_display()} — "
            f"{collecte.nb_fiches} fiche(s), {collecte.nb_erreurs} erreur(s)."
        )
        if collecte.message_erreur:
            self.stdout.write(self.style.WARNING(collecte.message_erreur))
