"""Point d'entrée WSGI (production, avec Gunicorn)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuration.parametres.dev")

application = get_wsgi_application()