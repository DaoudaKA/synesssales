from django.urls import path

from . import views

urlpatterns = [
    path("partenaires/", views.liste_partenaires, name="partenaires"),
]
