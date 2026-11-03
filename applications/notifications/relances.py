"""Détection des relances en retard et escalade au chef d'équipe."""
import datetime

from django.conf import settings
from django.utils import timezone

from applications.ventes.models import Tache

from . import evenements


def verifier_relances(maintenant=None, seuil_jours=None):
    """Alerte les commerciaux dont une tâche est en retard, puis escalade au chef.

    - Chaque tâche « à faire » dont l'échéance est passée alerte son responsable.
    - Si le retard atteint le seuil (en jours), le chef de l'équipe du responsable
      est aussi alerté.
    - Les clés de regroupement garantissent une alerte unique par tâche et par
      personne : la commande peut être relancée sans créer de doublons.

    Retourne un bilan chiffré.
    """
    maintenant = maintenant or timezone.now()
    if seuil_jours is None:
        seuil_jours = getattr(settings, "SEUIL_ESCALADE_RELANCES_JOURS", 2)

    en_retard = Tache.objects.filter(
        statut=Tache.Statut.A_FAIRE, echeance__lt=maintenant, responsable__isnull=False
    ).select_related("prospect", "responsable", "responsable__equipe__chef_equipe")

    bilan = {"en_retard": 0, "alertes": 0, "escalades": 0, "sans_chef": 0}
    for tache in en_retard:
        bilan["en_retard"] += 1
        if evenements.relance_en_retard(tache):
            bilan["alertes"] += 1

        retard = maintenant - tache.echeance
        if retard < datetime.timedelta(days=seuil_jours):
            continue
        equipe = tache.responsable.equipe
        chef = equipe.chef_equipe if equipe is not None else None
        if chef is None:
            # Personne à qui escalader : à signaler pour corriger l'organisation.
            bilan["sans_chef"] += 1
        elif chef != tache.responsable:
            if evenements.relance_escaladee(tache, chef, retard.days):
                bilan["escalades"] += 1
    return bilan


def verifier_rappels(maintenant=None, delai_echeance_heures=None, delai_rdv_heures=None):
    """Rappelle les tâches qui approchent de leur échéance et les rendez-vous imminents.

    - un rendez-vous qui commence dans le délai prévu → « rendez-vous imminent » ;
    - toute autre tâche à faire dont l'échéance tombe dans le délai prévu → rappel.
    Les clés de regroupement évitent tout doublon si la commande tourne souvent.
    """
    maintenant = maintenant or timezone.now()
    if delai_echeance_heures is None:
        delai_echeance_heures = getattr(settings, "DELAI_RAPPEL_ECHEANCE_HEURES", 24)
    if delai_rdv_heures is None:
        delai_rdv_heures = getattr(settings, "DELAI_RDV_IMMINENT_HEURES", 2)

    horizon = maintenant + datetime.timedelta(hours=max(delai_echeance_heures, delai_rdv_heures))
    a_venir = Tache.objects.filter(
        statut=Tache.Statut.A_FAIRE,
        echeance__gte=maintenant,
        echeance__lte=horizon,
        responsable__isnull=False,
    ).select_related("prospect", "responsable")

    bilan = {"relances_a_echeance": 0, "rdv_imminents": 0}
    for tache in a_venir:
        reste = tache.echeance - maintenant
        if tache.type == Tache.Type.RENDEZ_VOUS:
            if reste <= datetime.timedelta(hours=delai_rdv_heures):
                if evenements.rendez_vous_imminent(tache):
                    bilan["rdv_imminents"] += 1
        elif reste <= datetime.timedelta(hours=delai_echeance_heures):
            if evenements.relance_a_echeance(tache):
                bilan["relances_a_echeance"] += 1
    return bilan
