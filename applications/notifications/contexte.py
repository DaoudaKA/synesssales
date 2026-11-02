"""Contexte commun à toutes les pages : le nombre de notifications non lues."""
from .models import Notification


def non_lues(request):
    """Alimente la cloche du bandeau. Rien pour un visiteur non connecté."""
    if not request.user.is_authenticated:
        return {}
    nombre = Notification.objects.filter(destinataire=request.user, lue=False).count()
    return {"nombre_notifications": nombre}
