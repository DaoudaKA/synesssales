"""Calculs du tableau de bord commercial (chiffres clés et résultats comparés)."""
from django.db.models import Count, Q
from django.utils import timezone

from applications.comptes.permissions import a_le_droit, portees_consultation

from .models import Contrat, Prospect, Tache


def prospects_du_tableau(utilisateur):
    """Prospects que la personne a le droit de voir dans le tableau de bord.

    Suit la ligne « Tableaux de bord » de la matrice :
    - portée « toute » : tous les prospects ;
    - portée « périmètre » : ceux de son équipe (ou de l'équipe qu'elle dirige) ;
    - portée « propre » : ceux qu'elle suit elle-même.
    Sans droit de consultation, aucun prospect.
    """
    etendues = portees_consultation(utilisateur, "Tableaux de bord")
    if "toute" in etendues:
        return Prospect.objects.all()
    condition = Q()
    if "perimetre" in etendues:
        condition |= Q(equipe__chef_equipe=utilisateur)
        if utilisateur.equipe_id is not None:
            condition |= Q(equipe_id=utilisateur.equipe_id)
    if "propre" in etendues:
        condition |= Q(commercial=utilisateur)
    if not condition:
        return Prospect.objects.none()
    return Prospect.objects.filter(condition)


def _taux(gagnes, total):
    """Pourcentage arrondi (0 quand il n'y a aucun prospect)."""
    return round(100 * gagnes / total) if total else 0


def indicateurs(prospects, utilisateur, maintenant=None):
    """Chiffres clés sur les prospects fournis.

    Le taux de conversion est : prospects gagnés / total des prospects de la portée.
    """
    maintenant = maintenant or timezone.now()
    total = prospects.count()
    gagnes = prospects.filter(statut=Prospect.Statut.GAGNE).count()

    # Répartition par statut, dans l'ordre du parcours commercial (même les statuts à 0).
    comptes = dict(
        prospects.order_by().values_list("statut").annotate(n=Count("id")).values_list(
            "statut", "n"
        )
    )
    par_statut = [
        {"libelle": libelle, "total": comptes.get(code, 0)}
        for code, libelle in Prospect.Statut.choices
    ]

    en_retard = Tache.objects.filter(
        statut=Tache.Statut.A_FAIRE, echeance__lt=maintenant, prospect__in=prospects
    ).count()

    # Les contrats à valider ne concernent que les personnes habilitées (droit V).
    contrats_a_valider = None
    if a_le_droit(utilisateur, "Contrats", "V"):
        contrats_a_valider = (
            Contrat.objects.filter(
                statut_validation=Contrat.StatutValidation.SOUMIS, prospect__in=prospects
            )
            .exclude(prospect__commercial=utilisateur)
            .count()
        )

    return {
        "total": total,
        "gagnes": gagnes,
        "taux_conversion": _taux(gagnes, total),
        "par_statut": par_statut,
        "relances_en_retard": en_retard,
        "contrats_a_valider": contrats_a_valider,
    }


def ventilation(prospects, champ):
    """Résultats regroupés selon un champ (équipe, produit, campagne, zone).

    Retourne une liste de lignes {libelle, total, gagnes, taux}, les plus fournies d'abord.
    """
    lignes = (
        prospects.order_by()
        .values(champ)
        .annotate(
            total=Count("id"), gagnes=Count("id", filter=Q(statut=Prospect.Statut.GAGNE))
        )
        .order_by("-total", champ)
    )
    return [
        {
            "libelle": ligne[champ] or "Non renseigné",
            "total": ligne["total"],
            "gagnes": ligne["gagnes"],
            "taux": _taux(ligne["gagnes"], ligne["total"]),
        }
        for ligne in lignes
    ]
