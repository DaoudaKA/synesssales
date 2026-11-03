"""Commande « verifier_relances » : retards, escalades, rappels d'échéance et rendez-vous.

À planifier à intervalle court (par exemple toutes les 15 minutes) pour que les
rendez-vous imminents soient signalés à temps.
"""
from django.core.management.base import BaseCommand

from applications.notifications.relances import verifier_rappels, verifier_relances


class Command(BaseCommand):
    help = (
        "Alerte des relances en retard (avec escalade au chef d'équipe), "
        "des échéances proches et des rendez-vous imminents."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seuil-jours",
            type=int,
            default=None,
            help="Jours de retard avant escalade (par défaut : réglage du projet).",
        )

    def handle(self, *args, **options):
        bilan = verifier_relances(seuil_jours=options["seuil_jours"])
        rappels = verifier_rappels()
        self.stdout.write(
            f"{bilan['en_retard']} tâche(s) en retard ; "
            f"{bilan['alertes']} alerte(s) commercial ; "
            f"{bilan['escalades']} escalade(s) au chef d'équipe."
        )
        self.stdout.write(
            f"{rappels['relances_a_echeance']} rappel(s) d'échéance ; "
            f"{rappels['rdv_imminents']} rendez-vous imminent(s)."
        )
        if bilan["sans_chef"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{bilan['sans_chef']} tâche(s) à escalader sans chef d'équipe défini."
                )
            )
