"""Adresses de l'application ventes."""
from django.urls import path

from . import views

urlpatterns = [
    path("prospects/", views.liste_prospects, name="prospects"),
    path("affectations/", views.liste_affectations, name="affectations"),
]
