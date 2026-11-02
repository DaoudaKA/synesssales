"""Adresses de l'application ventes."""
from django.urls import path

from . import views

urlpatterns = [
    path("prospects/", views.liste_prospects, name="prospects"),
    path("affectations/", views.liste_affectations, name="affectations"),
    path("prospects/<int:pk>/", views.fiche_prospect, name="prospect"),
    path(
        "prospects/<int:pk>/activites/nouvelle/",
        views.nouvelle_activite,
        name="nouvelle_activite",
    ),
    path("prospects/<int:pk>/taches/nouvelle/", views.nouvelle_tache, name="nouvelle_tache"),
    path("taches/<int:pk>/faite/", views.tache_faite, name="tache_faite"),
    path("relances/", views.mes_relances, name="relances"),
    path(
        "prospects/<int:pk>/contrats/nouveau/",
        views.nouveau_contrat,
        name="nouveau_contrat",
    ),
    path("contrats/a-valider/", views.contrats_a_valider, name="contrats_a_valider"),
    path("contrats/<int:pk>/decision/", views.decision_contrat, name="decision_contrat"),
]
