"""Événements métier qui déclenchent des notifications (matrice du cahier des charges).

Chaque fonction décide qui prévenir, avec quel message, quelle priorité et quel lien.
Le moteur générique (`notifier`) se charge de créer la notification sans doublon.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from applications.comptes.permissions import portees

from .models import Notification
from .services import notifier

# Types de notification (colonne « type » du modèle).
AFFECTATION_PRODUIT = "affectation_produit"
PROSPECT_AFFECTE = "prospect_affecte"
PROSPECT_RETIRE = "prospect_retire"
CONTRAT_A_VALIDER = "contrat_a_valider"
CONTRAT_VALIDE = "contrat_valide"
CONTRAT_REFUSE = "contrat_refuse"
RELANCE_EN_RETARD = "relance_en_retard"
RELANCE_ESCALADEE = "relance_escaladee"
RELANCE_A_ECHEANCE = "relance_a_echeance"
RDV_IMMINENT = "rdv_imminent"


def _lien_prospect(prospect):
    """Adresse de la fiche du prospect."""
    return reverse("prospect", args=[prospect.pk])


def affectation_produit(affectation):
    """Prévient une personne qu'elle vient d'être affectée à un produit."""
    notifier(
        affectation.utilisateur,
        AFFECTATION_PRODUIT,
        f"Vous êtes affecté(e) au produit « {affectation.produit} » "
        f"à partir du {affectation.date_debut:%d/%m/%Y}.",
    )


def prospect_reaffecte(prospect, ancien, auteur, motif=""):
    """Prévient le nouveau commercial (et l'ancien) d'un changement d'affectation."""
    nouveau = prospect.commercial
    # On ne notifie pas quelqu'un de sa propre action.
    if nouveau is not None and nouveau != auteur:
        message = f"Le prospect « {prospect.nom} » vous a été affecté."
        if motif:
            message += f" Motif : {motif}"
        notifier(
            nouveau, PROSPECT_AFFECTE, message, lien=_lien_prospect(prospect)
        )
    if ancien is not None and ancien != auteur:
        # Pas de lien : l'ancien commercial n'a peut-être plus accès à la fiche.
        notifier(
            ancien,
            PROSPECT_RETIRE,
            f"Le prospect « {prospect.nom} » a été confié à un autre commercial.",
        )


def validateurs_du_contrat(contrat):
    """Personnes habilitées (droit V sur les contrats) à décider de ce contrat.

    - portée « toute » : tous les validateurs ;
    - portée « périmètre » : seulement ceux de l'équipe du prospect ;
    - le commercial propriétaire du prospect ne valide jamais son propre contrat.
    """
    prospect = contrat.prospect
    equipe = prospect.equipe
    retenus = []
    for personne in get_user_model().objects.filter(statut="actif").distinct():
        if personne.pk == prospect.commercial_id:
            continue
        etendues = portees(personne, "Contrats", "V")
        if "toute" in etendues:
            retenus.append(personne)
        elif "perimetre" in etendues and equipe is not None and (
            equipe.chef_equipe_id == personne.pk or personne.equipe_id == equipe.pk
        ):
            retenus.append(personne)
    return retenus


def contrat_soumis(contrat):
    """Prévient les validateurs qu'un contrat attend une décision."""
    for validateur in validateurs_du_contrat(contrat):
        notifier(
            validateur,
            CONTRAT_A_VALIDER,
            f"Un contrat est à valider pour le prospect « {contrat.prospect.nom} ».",
            priorite=Notification.Priorite.HAUTE,
            # Vers la liste des contrats à valider : la fiche peut être inaccessible
            # à un responsable sans équipe (décision 55).
            lien=reverse("contrats_a_valider"),
            cle=f"contrat-a-valider:{contrat.pk}",
        )


def contrat_decide(contrat):
    """Prévient le commercial du prospect de la décision prise sur son contrat."""
    prospect = contrat.prospect
    commercial = prospect.commercial
    # Pas de notification si le commercial est lui-même l'auteur de la décision.
    if commercial is None or commercial == contrat.valide_par:
        return
    if contrat.statut_validation == contrat.StatutValidation.VALIDE:
        type_, priorite = CONTRAT_VALIDE, Notification.Priorite.MOYENNE
        message = f"Votre contrat pour « {prospect.nom} » a été validé."
    else:
        type_, priorite = CONTRAT_REFUSE, Notification.Priorite.HAUTE
        message = (
            f"Votre contrat pour « {prospect.nom} » a été refusé. "
            f"Motif : {contrat.motif_refus}"
        )
    notifier(
        commercial,
        type_,
        message,
        priorite=priorite,
        lien=_lien_prospect(prospect),
        cle=f"contrat-decision:{contrat.pk}",
    )


def relance_en_retard(tache):
    """Prévient le commercial qu'une de ses tâches a dépassé son échéance.

    Retourne True si l'alerte vient d'être créée (False si elle existait déjà).
    """
    prospect = tache.prospect
    _, creee = notifier(
        tache.responsable,
        RELANCE_EN_RETARD,
        f"Tâche en retard ({tache.get_type_display()}) pour « {prospect.nom} » : "
        f"l'échéance était le {timezone.localtime(tache.echeance):%d/%m/%Y à %H:%M}.",
        priorite=Notification.Priorite.HAUTE,
        lien=_lien_prospect(prospect),
        cle=f"relance-en-retard:{tache.pk}",
    )
    return creee


def relance_escaladee(tache, chef, jours):
    """Prévient le chef d'équipe qu'une tâche de son équipe traîne depuis `jours` jours.

    Retourne True si l'alerte vient d'être créée (une seule fois par tâche).
    """
    prospect = tache.prospect
    _, creee = notifier(
        chef,
        RELANCE_ESCALADEE,
        f"{tache.responsable.nom} a une tâche ({tache.get_type_display()}) en retard "
        f"de {jours} jour(s) pour « {prospect.nom} ».",
        priorite=Notification.Priorite.HAUTE,
        lien=_lien_prospect(prospect),
        cle=f"relance-escaladee:{tache.pk}",
    )
    return creee



def relance_a_echeance(tache):
    """Rappelle au commercial une tâche dont l'échéance approche.

    Retourne True si le rappel vient d'être créé (une seule fois par tâche).
    """
    prospect = tache.prospect
    _, creee = notifier(
        tache.responsable,
        RELANCE_A_ECHEANCE,
        f"À faire avant le {timezone.localtime(tache.echeance):%d/%m/%Y à %H:%M} "
        f"({tache.get_type_display()}) pour « {prospect.nom} ».",
        priorite=Notification.Priorite.HAUTE,
        lien=_lien_prospect(prospect),
        cle=f"relance-a-echeance:{tache.pk}",
    )
    return creee


def rendez_vous_imminent(tache):
    """Prévient le commercial qu'un rendez-vous approche.

    Retourne True si l'alerte vient d'être créée (une seule fois par rendez-vous).
    """
    prospect = tache.prospect
    _, creee = notifier(
        tache.responsable,
        RDV_IMMINENT,
        f"Rendez-vous à {timezone.localtime(tache.echeance):%H:%M} le "
        f"{timezone.localtime(tache.echeance):%d/%m/%Y} avec « {prospect.nom} » : "
        "pensez à le préparer.",
        priorite=Notification.Priorite.HAUTE,
        lien=_lien_prospect(prospect),
        cle=f"rdv-imminent:{tache.pk}",
    )
    return creee
