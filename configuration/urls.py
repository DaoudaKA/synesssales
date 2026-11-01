"""Adresses principales du projet."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("applications.comptes.urls")),
    path("", include("applications.noyau.urls")),
    path("", include("applications.ventes.urls")),
    path("", include("applications.partenaires.urls")),
]
