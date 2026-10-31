"""Services du pilotage commercial."""
import datetime

from django.db import transaction

from .models import Affectation


@transaction.atomic
def affecter(utilisateur, produit, date_debut, campagne=None):
    """Affecte un commercial à un produit, sans perdre l'historique.

    Les affectations encore ouvertes de la personne sont clôturées la veille du
    nouveau début (ou le jour même si elles ont commencé ce jour-là).
    """
    veille = date_debut - datetime.timedelta(days=1)
    ouvertes = Affectation.objects.filter(utilisateur=utilisateur, date_fin__isnull=True)
    for ancienne in ouvertes:
        ancienne.date_fin = max(ancienne.date_debut, veille)
        ancienne.save(update_fields=["date_fin"])
    return Affectation.objects.create(
        utilisateur=utilisateur, produit=produit, campagne=campagne, date_debut=date_debut
    )
