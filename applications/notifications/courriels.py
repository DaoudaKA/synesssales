"""Envoi par e-mail des notifications qui le demandent (plan, section 6)."""
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification


def _corps(notification):
    """Texte du message, suivi d'un lien absolu vers la page concernée."""
    corps = notification.message
    if notification.lien:
        base = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
        corps += f"\n\nOuvrir dans SYNESS Sales : {base}{notification.lien}"
    return corps


def envoyer_courriels(plafond=None):
    """Envoie les e-mails en attente ; retourne un bilan chiffré.

    - seules les notifications qui le demandent (`par_courriel`) et pas encore
      envoyées sont traitées, du plus ancien au plus récent ;
    - les comptes suspendus ne reçoivent rien ;
    - un échec est enregistré et réessayé à l'exécution suivante, jusqu'à
      COURRIEL_MAX_TENTATIVES ;
    - au plus `plafond` e-mails par exécution : le reste attend la suivante.
    """
    max_tentatives = getattr(settings, "COURRIEL_MAX_TENTATIVES", 3)
    if plafond is None:
        plafond = getattr(settings, "COURRIEL_PLAFOND_PAR_EXECUTION", 100)

    en_attente = Notification.objects.filter(
        par_courriel=True,
        courriel_envoye_le__isnull=True,
        courriel_tentatives__lt=max_tentatives,
        destinataire__statut="actif",
    ).select_related("destinataire")
    total = en_attente.count()
    lot = list(en_attente.order_by("date")[:plafond])

    bilan = {"envoyes": 0, "echecs": 0, "restants": total - len(lot)}
    for notification in lot:
        # L'objet tient sur une ligne : on retire les éventuels retours à la ligne.
        sujet = "[SYNESS Sales] " + " ".join(notification.message[:70].split())
        notification.courriel_tentatives += 1
        try:
            send_mail(
                sujet,
                _corps(notification),
                None,  # expéditeur : DEFAULT_FROM_EMAIL
                [notification.destinataire.email],
                fail_silently=False,
            )
        except Exception as erreur:  # noqa: BLE001 - toute panne d'envoi est à consigner
            notification.courriel_erreur = str(erreur)[:200]
            bilan["echecs"] += 1
        else:
            notification.courriel_envoye_le = timezone.now()
            notification.courriel_erreur = ""
            bilan["envoyes"] += 1
        notification.save(
            update_fields=["courriel_tentatives", "courriel_erreur", "courriel_envoye_le"]
        )
    return bilan
