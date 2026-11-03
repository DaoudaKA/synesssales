"""Résumé hebdomadaire envoyé à la Direction et aux responsables."""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone

from applications.comptes.permissions import portees_consultation
from applications.ventes.tableau_de_bord import indicateurs, prospects_du_tableau

from . import evenements


def envoyer_resumes(aujourdhui=None):
    """Crée le résumé de la semaine pour chaque personne qui voit tous les indicateurs.

    Chaque résumé reprend le tableau de bord de la personne, donc ses propres droits.
    Retourne un bilan chiffré.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    depuis = timezone.now() - datetime.timedelta(days=7)

    bilan = {"destinataires": 0, "crees": 0}
    for personne in get_user_model().objects.filter(statut="actif"):
        # Direction et responsables : portée « toute » sur les tableaux de bord.
        if "toute" not in portees_consultation(personne, "Tableaux de bord"):
            continue
        bilan["destinataires"] += 1
        prospects = prospects_du_tableau(personne)
        chiffres = indicateurs(prospects, personne)
        nouveaux = prospects.filter(date_creation__gte=depuis).count()
        if evenements.resume_periodique(personne, chiffres, nouveaux, aujourdhui):
            bilan["crees"] += 1
    return bilan
