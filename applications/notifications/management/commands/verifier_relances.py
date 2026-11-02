"""Commande « verifier_relances » : à lancer chaque jour (tâche planifiée)."""
from django.core.management.base import BaseCommand

from applications.notifications.relances import verifier_relances


class Command(BaseCommand):
    help = "Alerte les commerciaux des relances en retard et escalade au chef d'équipe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seuil-jours",
            type=int,
            default=None,
            help="Jours de retard avant escalade (par défaut : réglage du projet).",
        )

    def handle(self, *args, **options):
        bilan = verifier_relances(seuil_jours=options["seuil_jours"])
        self.stdout.write(
            f"{bilan['en_retard']} tâche(s) en retard ; "
            f"{bilan['alertes']} alerte(s) commercial ; "
            f"{bilan['escalades']} escalade(s) au chef d'équipe."
        )
        if bilan["sans_chef"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{bilan['sans_chef']} tâche(s) à escalader sans chef d'équipe défini."
                )
            )
