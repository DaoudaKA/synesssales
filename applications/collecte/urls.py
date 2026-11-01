from django.urls import path

from . import views

urlpatterns = [
    path("collectes/", views.liste_collectes, name="collectes"),
    path("collectes/importer/", views.importer, name="collecte_importer"),
]
