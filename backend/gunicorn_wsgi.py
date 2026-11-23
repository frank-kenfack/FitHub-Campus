"""Point d'entree Gunicorn avec monkey-patching eventlet pour Socket.IO."""

import eventlet

eventlet.monkey_patch()

from wsgi import app  # noqa: E402, F401
