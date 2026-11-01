from django.urls import path

from . import views

urlpatterns = [
    path("partenaires/", views.liste_partenaires, name="partenaires"),
    path("partenaires/nouveau/", views.nouveau_partenaire, name="partenaire_nouveau"),
]
