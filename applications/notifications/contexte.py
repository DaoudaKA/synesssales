"""Contexte ajouté à toutes les pages : compteur de notifications et accès au paramétrage."""
from applications.comptes.permissions import peut_consulter


def non_lues(request):
    """Nombre de notifications non lues, et droit d'ouvrir le paramétrage."""
    utilisateur = request.user
    if not utilisateur.is_authenticated:
        return {"nombre_notifications": 0, "peut_parametrer_notifications": False}
    return {
        "nombre_notifications": utilisateur.notifications.filter(lue=False).count(),
        "peut_parametrer_notifications": peut_consulter(
            utilisateur, "Notifications (paramétrage)"
        ),
    }
