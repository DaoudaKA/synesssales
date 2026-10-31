"""Réglages communs à tous les tests."""
import pytest


@pytest.fixture(autouse=True)
def hachage_rapide(settings):
    """Accélère les tests : un hachage de mot de passe léger, jamais utilisé en vrai."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
