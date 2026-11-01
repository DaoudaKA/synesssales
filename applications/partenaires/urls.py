from django.urls import path

from . import views

urlpatterns = [
    path("partenaires/", views.liste_partenaires, name="partenaires"),
    path("partenaires/nouveau/", views.nouveau_partenaire, name="partenaire_nouveau"),
    path("partenaires/doublons/", views.liste_doublons, name="doublons"),
    path(
        "partenaires/<int:pk>/verifier/",
        views.verifier_partenaire,
        name="partenaire_verification",
    ),
    path("partenaires/doublons/<int:pk>/rejeter/",
          views.rejeter_doublon, name="doublon_rejet"),
    path(
        "partenaires/doublons/<int:pk>/fusionner/",
        views.fusionner_doublon,
        name="doublon_fusion",
    )
]
