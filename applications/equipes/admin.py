"""Administration des équipes."""
from django.contrib import admin

from applications.comptes.models import Utilisateur

from .models import Equipe


class MembreInline(admin.TabularInline):
    model = Utilisateur
    fields = ["nom", "email", "statut"]
    readonly_fields = ["nom", "email", "statut"]
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "membre"
    verbose_name_plural = "membres"


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["nom", "chef_equipe", "date_creation"]
    search_fields = ["nom"]
    inlines = [MembreInline]
