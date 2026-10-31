"""Administration des comptes."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import PermissionMetier, Role, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
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


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["nom", "description"]
    filter_horizontal = ["permissions"]


@admin.register(PermissionMetier)
class PermissionMetierAdmin(admin.ModelAdmin):
    list_display = ["ressource", "action", "portee"]
    list_filter = ["action", "portee"]
    search_fields = ["ressource"]
