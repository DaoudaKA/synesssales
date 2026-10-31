"""Commande : charge les rôles et permissions de la matrice (annexe G)."""
from django.core.management.base import BaseCommand

from applications.comptes.matrice import charger_matrice


class Command(BaseCommand):
    help = "Charge les rôles et les permissions de la matrice de l'annexe G."

    def handle(self, *args, **options):
        nombre = charger_matrice()
        self.stdout.write(self.style.SUCCESS(f"{nombre} rôles chargés."))
