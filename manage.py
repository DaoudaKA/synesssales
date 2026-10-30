#!/usr/bin/env python
"""Point d'entrée des commandes d'administration de Django."""
import os
import sys


def main():
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "configuration.parametres.dev"
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as erreur:
        raise ImportError(
            "Django est introuvable. L'environnement virtuel (.venv) "
            "est-il activé ?"
        ) from erreur
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()