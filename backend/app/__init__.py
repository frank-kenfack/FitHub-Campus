"""Factory de l'application Flask FitHub Campus."""

import os

from flask import Flask
from flask_cors import CORS

from app import models  # noqa: F401
from app.config import Config
from app.extensions import db, jwt, migrate, socketio
from app.routes.health import health_bp


def create_app(config_class: type[Config] = Config) -> Flask:
    """Construit et configure l'instance Flask principale."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="threading" if app.testing else None,
    )

    app.register_blueprint(health_bp)
    return app
