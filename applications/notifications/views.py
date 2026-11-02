"""Écrans des notifications : chacun ne voit et ne modifie que les siennes."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def liste_notifications(request):
    """Mes notifications : les non lues d'abord, puis les plus récentes."""
    notifications = Notification.objects.filter(destinataire=request.user).order_by(
        "lue", "-date", "-id"
    )[:100]
    return render(request, "notifications/liste.html", {"notifications": notifications})


@login_required
@require_POST  # modifier des données ne se fait jamais par un simple lien
def marquer_lue(request, pk):
    """Marque une de mes notifications comme lue (404 si ce n'est pas la mienne)."""
    notification = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    notification.lue = True
    notification.save(update_fields=["lue"])
    return redirect("notifications")


@login_required
@require_POST
def tout_marquer_lu(request):
    """Marque toutes mes notifications comme lues."""
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    return redirect("notifications")
