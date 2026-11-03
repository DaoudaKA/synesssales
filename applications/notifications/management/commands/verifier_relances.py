"""Commande « verifier_relances » : retards, escalades, rappels, rendez-vous, prospects sans suivi.

À planifier à intervalle court (par exemple toutes les 15 minutes) pour que les
rendez-vous imminents soient signalés à temps.
"""
from django.core.management.base import BaseCommand

from applications.notifications.relances import (
    verifier_rappels,
    verifier_relances,
    verifier_sans_suivi,
)


class Command(BaseCommand):
    help = (
        "Alerte des relances en retard (avec escalade au chef d'équipe), des échéances "
        "proches, des rendez-vous imminents et des prospects sans suivi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seuil-jours",
            type=int,
            default=None,
            help="Jours de retard avant escalade (par défaut : réglage du projet).",
        )
        parser.add_argument(
            "--seuil-sans-suivi",
            type=int,
            default=None,
            help="Jours sans activité avant alerte « sans suivi » (par défaut : réglage).",
        )

    def handle(self, *args, **options):
        bilan = verifier_relances(seuil_jours=options["seuil_jours"])
        rappels = verifier_rappels()
        suivi = verifier_sans_suivi(seuil_jours=options["seuil_sans_suivi"])
        self.stdout.write(
            f"{bilan['en_retard']} tâche(s) en retard ; "
            f"{bilan['alertes']} alerte(s) commercial ; "
            f"{bilan['escalades']} escalade(s) au chef d'équipe."
        )
        self.stdout.write(
            f"{rappels['relances_a_echeance']} rappel(s) d'échéance ; "
            f"{rappels['rdv_imminents']} rendez-vous imminent(s)."
        )
        self.stdout.write(f"{suivi['sans_suivi']} prospect(s) sans suivi signalé(s).")
        if bilan["sans_chef"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{bilan['sans_chef']} tâche(s) à escalader sans chef d'équipe défini."
                )
            )
