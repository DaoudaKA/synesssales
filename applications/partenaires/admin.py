"""Administration des partenaires."""
from django.contrib import admin

from .models import Categorie, Contact, Localisation, Partenaire, ServicePropose


class LocalisationInline(admin.TabularInline):
    model = Localisation
    extra = 0


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0


class ServiceInline(admin.TabularInline):
    model = ServicePropose
    extra = 0


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ["nom", "type", "categorie_parent"]
    list_filter = ["type"]
    search_fields = ["nom"]


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = [
        "nom_commercial",
        "categorie",
        "statut_verification",
        "date_derniere_verification",
        "statut_commercial",
    ]
    list_filter = ["statut_verification", "statut_commercial", "categorie"]
    search_fields = ["nom_commercial", "raison_sociale"]
    date_hierarchy = "date_creation"
    inlines = [LocalisationInline, ContactInline, ServiceInline]
