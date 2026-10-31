"""Services de l'application comptes : journal d'audit."""
from .models import JournalAudit


def journaliser(utilisateur, action, ressource, objet_id="", detail=""):
    """Enregistre une action sensible : qui, quoi, sur quel objet."""
    auteur = utilisateur if getattr(utilisateur, "is_authenticated", False) else None
    return JournalAudit.objects.create(
        utilisateur=auteur,
        action=action,
        ressource=str(ressource),
        objet_id=str(objet_id),
        detail=detail,
    )


class AdminJournalise:
    """À placer avant ModelAdmin : journalise les suppressions faites dans l'administration."""

    def delete_model(self, request, obj):
        journaliser(
            request.user, "suppression", self.model._meta.verbose_name, obj.pk, str(obj)
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            journaliser(
                request.user, "suppression", self.model._meta.verbose_name, obj.pk, str(obj)
            )
        super().delete_queryset(request, queryset)
