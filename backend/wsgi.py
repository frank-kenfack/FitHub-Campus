"""Point d'entree WSGI standard (sans eventlet) pour Flask CLI et Pytest."""

from app import create_app

app = create_app()
