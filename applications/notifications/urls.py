"""Adresses de l'application notifications."""
from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.liste_notifications, name="notifications"),
    path("notifications/tout-lu/", views.tout_marquer_lu, name="notifications_tout_lu"),
    path("notifications/<int:pk>/lue/", views.marquer_lue, name="notification_lue"),
]
