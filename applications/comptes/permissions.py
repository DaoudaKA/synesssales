"""Contrôle des droits d'après la matrice des rôles (annexe G)."""
from django.db.models import Q

from .models import PermissionMetier


def portees(utilisateur, ressource, action):
    """Retourne l'ensemble des portées accordées. Un ensemble vide signifie un refus.

    Les droits viennent uniquement des rôles : ni un compte administrateur Django
    ni un compte sans rôle n'a de droit supplémentaire, pour que la matrice reste
    la seule source de vérité.
    """
    if not (utilisateur.is_authenticated and utilisateur.is_active):
        return set()
    return set(
        PermissionMetier.objects.filter(
            roles__utilisateurs=utilisateur, ressource=ressource, action=action
        )
        .values_list("portee", flat=True)
        .distinct()
    )


def a_le_droit(utilisateur, ressource, action):
    """Indique si l'utilisateur a ce droit, quelle que soit sa portée."""
    return bool(portees(utilisateur, ressource, action))


def restreindre(queryset, utilisateur, ressource, proprietaire, equipe, chef_equipe):
    """Limite une requête aux lignes que l'utilisateur a le droit de consulter.

    proprietaire : champ qui désigne la personne concernée (portée « propre »).
    equipe : chemin vers l'équipe de la ligne (portée « périmètre »).
    chef_equipe : chemin vers le chef de cette équipe.
    """
    accordees = portees(utilisateur, ressource, "L")
    if "toute" in accordees:
        return queryset
    conditions = Q(pk__in=[])
    if "propre" in accordees:
        conditions |= Q(**{proprietaire: utilisateur})
    if "perimetre" in accordees:
        if utilisateur.equipe_id is not None:
            conditions |= Q(**{f"{equipe}_id": utilisateur.equipe_id})
        conditions |= Q(**{chef_equipe: utilisateur})
    return queryset.filter(conditions)
