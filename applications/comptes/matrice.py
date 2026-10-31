"""Matrice des rôles et permissions (cahier des charges, annexe G).

Cellules : L consulter, C créer, M modifier, V valider, S supprimer, E exporter,
A administrer. Un * limite au périmètre de la personne (équipe, produit, zone) ;
(p) limite à ses propres données ; — signifie aucun accès.
"""
from django.db import transaction

from .models import PermissionMetier, Role

ROLES = [
    (
        "Administrateur système",
        "Configuration générale, utilisateurs, rôles, sécurité, paramètres",
    ),
    ("Direction", "Vision globale, résultats consolidés, pilotage stratégique"),
    (
        "Responsable commercial",
        "Gestion des équipes, objectifs, campagnes, performances",
    ),
    (
        "Chef d'équipe",
        "Supervision de son équipe, affectation des prospects, suivi des activités",
    ),
    (
        "Commercial",
        "Prospection, appels, visites, comptes rendus, contrats, relances",
    ),
    (
        "Responsable data",
        "Contrôle de la collecte, qualité, doublons, validation des données",
    ),
    (
        "Analyste ou responsable métier",
        "Consultation des indicateurs et analyse des résultats",
    ),
    (
        "Lecteur autorisé",
        "Consultation limitée aux données et rapports autorisés",
    ),
]

# Une ligne par ressource, une cellule par rôle, dans l'ordre de ROLES.
RESSOURCES = [
    ("Utilisateurs, rôles, permissions", ["CMSA", "—", "L*", "—", "—", "—", "—", "—"]),
    ("Produits et argumentaires", ["CMS", "L", "CM", "L*", "L*", "—", "L", "L*"]),
    ("Équipes et affectations", ["CMS", "L", "CMS*", "LM*", "L (p)", "—", "L", "—"]),
    ("Campagnes et objectifs", ["L", "L", "CMS", "L*", "L*", "—", "L", "L*"]),
    ("Fiches partenaires", ["L", "L", "L", "L", "L", "CMVSE", "LE", "L*"]),
    ("Collectes et imports", ["L", "—", "—", "—", "—", "CML", "L", "—"]),
    ("Intégration Garage.sn", ["CMA", "—", "—", "—", "—", "ML", "L", "—"]),
    ("Prospects", ["—", "L", "LM*", "CML*", "CML (p)", "—", "L", "L*"]),
    ("Activités et relances", ["—", "L", "L", "L*", "CML (p)", "—", "L", "L*"]),
    ("Contrats", ["—", "L", "LV", "L*", "CL (p)", "—", "L", "—"]),
    ("Scripts de prospection", ["L", "L", "CMV", "CL*", "CL", "—", "L", "—"]),
    ("Enregistrements vocaux", ["A", "—", "L*", "L*", "L (p)", "—", "—", "—"]),
    ("Tableaux de bord", ["—", "L", "L", "L*", "L (p)", "L", "L", "L*"]),
    ("Notifications (paramétrage)", ["CMA", "—", "M*", "—", "—", "—", "—", "—"]),
    ("Exports de données", ["—", "E", "E*", "E*", "—", "E", "E", "—"]),
    ("Journal d'audit", ["L", "—", "—", "—", "—", "—", "—", "L*"]),
]

ACTIONS_VALIDES = set(PermissionMetier.Action.values)


def analyser_cellule(texte):
    """Transforme une cellule du tableau en (actions, portée)."""
    texte = texte.strip()
    if texte in ("—", "-", ""):
        return "", PermissionMetier.Portee.TOUTE
    portee = PermissionMetier.Portee.TOUTE
    if texte.endswith("(p)"):
        portee = PermissionMetier.Portee.PROPRE
        texte = texte[:-3].strip()
    elif texte.endswith("*"):
        portee = PermissionMetier.Portee.PERIMETRE
        texte = texte[:-1].strip()
    inconnues = set(texte) - ACTIONS_VALIDES
    if inconnues:
        raise ValueError(f"Actions inconnues dans la cellule : {sorted(inconnues)}")
    return texte, portee


def droits_attendus():
    """Retourne {rôle: {ressource: {(action, portée), ...}}} d'après le tableau."""
    attendus = {nom: {} for nom, _ in ROLES}
    for ressource, cellules in RESSOURCES:
        for (nom, _), cellule in zip(ROLES, cellules, strict=True):
            actions, portee = analyser_cellule(cellule)
            attendus[nom][ressource] = {(action, portee) for action in actions}
    return attendus


@transaction.atomic
def charger_matrice():
    """Crée ou met à jour les rôles et leurs permissions. Peut être relancé sans risque."""
    descriptions = dict(ROLES)
    for nom, par_ressource in droits_attendus().items():
        role, _ = Role.objects.update_or_create(
            nom=nom, defaults={"description": descriptions[nom]}
        )
        permissions = []
        for ressource, droits in par_ressource.items():
            for action, portee in sorted(droits):
                permission, _ = PermissionMetier.objects.get_or_create(
                    ressource=ressource, action=action, portee=portee
                )
                permissions.append(permission)
        role.permissions.set(permissions)
    return len(ROLES)
