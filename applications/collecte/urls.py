from django.urls import path

from . import views, vues_sources

urlpatterns = [
    path("collectes/", views.liste_collectes, name="collectes"),
    path("collectes/importer/", views.importer, name="collecte_importer"),
    path("sources/", vues_sources.liste_sources, name="sources"),
    path("sources/nouvelle/", vues_sources.nouvelle_source, name="source_nouvelle"),
    path("sources/<int:pk>/validation/", vues_sources.validation_source, name="source_validation"),
    path("sources/<int:pk>/revocation/", vues_sources.revocation_source, name="source_revocation"),
]
