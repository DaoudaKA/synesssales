"""Contrôle des droits d'après la matrice des rôles (annexe G)."""
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
