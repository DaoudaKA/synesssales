"""Administration des comptes."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import JournalAudit, PermissionMetier, Role, Utilisateur
from .services import AdminJournalise, journaliser


@admin.register(Utilisateur)
class UtilisateurAdmin(AdminJournalise, UserAdmin):
    ordering = ["nom"]
    list_display = ["nom", "email", "statut", "equipe", "is_staff"]
    list_filter = ["statut", "equipe", "roles"]
    search_fields = ["nom", "email"]
    filter_horizontal = ["roles", "groups", "user_permissions"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("nom", "statut", "equipe", "roles")}),
        ("Accès", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nom", "password1", "password2")}),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        champs = {"roles", "statut", "is_staff", "is_superuser"} & set(form.changed_data)
        if champs:
            journaliser(
                request.user,
                "modification_droits",
                "Utilisateurs",
                form.instance.pk,
                f"{form.instance.email} : {', '.join(sorted(champs))}",
            )


@admin.register(Role)
class RoleAdmin(AdminJournalise, admin.ModelAdmin):
    list_display = ["nom", "description"]
    filter_horizontal = ["permissions"]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change or "permissions" in form.changed_data:
            role = form.instance
            journaliser(
                request.user,
                "modification_droits",
                "Rôles",
                role.pk,
                f"{role.nom} : {role.permissions.count()} permission(s)",
            )


@admin.register(PermissionMetier)
class PermissionMetierAdmin(AdminJournalise, admin.ModelAdmin):
    list_display = ["ressource", "action", "portee"]
    list_filter = ["action", "portee"]
    search_fields = ["ressource"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        journaliser(request.user, "modification_droits", "Permissions métier", obj.pk, str(obj))


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    """Le journal se consulte, il ne se modifie pas."""

    list_display = ["date", "utilisateur", "action", "ressource", "objet_id"]
    list_filter = ["action", "ressource"]
    search_fields = ["detail", "objet_id", "utilisateur__email"]
    date_hierarchy = "date"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
