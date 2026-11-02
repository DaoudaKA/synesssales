"""Services des notifications : le seul endroit où l'on en crée."""
from .models import Notification


def notifier(
    destinataire,
    type_,
    message,
    priorite=Notification.Priorite.MOYENNE,
    canal=Notification.Canal.APPLICATION,
    lien="",
    cle="",
):
    """Envoie une notification et retourne (notification, créée).

    Avec une clé, la même alerte n'est créée qu'une fois pour un destinataire : un
    deuxième appel retourne la notification existante, sans en ajouter une autre.
    """
    # Le lien est affiché tel quel dans une page : on n'accepte que les adresses
    # internes, jamais un site extérieur.
    if lien and not lien.startswith("/"):
        raise ValueError("Le lien d'une notification doit être une adresse interne.")
    valeurs = {
        "type": type_,
        "message": message,
        "priorite": priorite,
        "canal": canal,
        "lien": lien,
    }
    if not cle:
        return Notification.objects.create(destinataire=destinataire, **valeurs), True
    # get_or_create s'appuie sur la contrainte d'unicité : sûr même si deux
    # traitements créent la même alerte en même temps.
    return Notification.objects.get_or_create(
        destinataire=destinataire, cle=cle, defaults=valeurs
    )
