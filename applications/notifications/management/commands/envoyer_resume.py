"""Commande « envoyer_resume » : résumé hebdomadaire de la Direction et des responsables.

À planifier une fois par semaine (par exemple le lundi matin). La relancer le même
jour ne crée pas de doublon.
"""
from django.core.management.base import BaseCommand

from applications.notifications.resume import envoyer_resumes


class Command(BaseCommand):
    help = "Crée le résumé hebdomadaire des indicateurs pour la Direction et les responsables."

    def handle(self, *args, **options):
        bilan = envoyer_resumes()
        self.stdout.write(
            f"{bilan['destinataires']} destinataire(s) ; {bilan['crees']} résumé(s) créé(s)."
        )
