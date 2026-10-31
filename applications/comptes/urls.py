"""Adresses de l'application comptes : connexion et déconnexion."""
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

urlpatterns = [
    path(
        "connexion/",
        LoginView.as_view(
            template_name="comptes/connexion.html", redirect_authenticated_user=True
        ),
        name="connexion",
    ),
    path("deconnexion/", LogoutView.as_view(), name="deconnexion"),
]
