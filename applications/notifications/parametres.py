"""Catalogue des seuils réglables et lecture de leur valeur courante."""
from django.conf import settings

from .models import Parametre

# Clé → libellé, unité, valeur par défaut et bornes acceptées.
PARAMETRES = {
    "SEUIL_ESCALADE_RELANCES_JOURS": {
        "libelle": "Escalade d'une relance en retard au chef d'équipe",
        "unite": "jours de retard",
        "defaut": 2,
        "min": 0,
        "max": 90,
    },
    "DELAI_RAPPEL_ECHEANCE_HEURES": {
        "libelle": "Rappel avant l'échéance d'une tâche",
        "unite": "heures avant l'échéance",
        "defaut": 24,
        "min": 1,
        "max": 168,
    },
    "DELAI_RDV_IMMINENT_HEURES": {
        "libelle": "Alerte avant un rendez-vous",
        "unite": "heures avant le rendez-vous",
        "defaut": 2,
        "min": 1,
        "max": 48,
    },
    "SEUIL_SANS_SUIVI_JOURS": {
        "libelle": "Prospect sans suivi signalé au chef d'équipe",
        "unite": "jours sans activité",
        "defaut": 7,
        "min": 1,
        "max": 90,
    },
    "TOLERANCE_ECART_OBJECTIF_POINTS": {
        "libelle": "Écart toléré avant d'alerter sur un objectif",
        "unite": "points de pourcentage",
        "defaut": 20,
        "min": 0,
        "max": 100,
    },
}


def valeur(cle):
    """Valeur courante d'un paramètre : enregistrée, sinon settings, sinon défaut.

    Lève KeyError pour une clé inconnue, afin de repérer vite une faute de frappe.
    """
    definition = PARAMETRES[cle]
    enregistree = Parametre.objects.filter(cle=cle).values_list("valeur", flat=True).first()
    if enregistree is not None:
        return enregistree
    return getattr(settings, cle, definition["defaut"])
