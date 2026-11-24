"""Factory de l'application Flask FitHub Campus."""

import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from app import models, sockets  # noqa: F401
from app.config import Config
from app.extensions import db, jwt, migrate, socketio
from app.routes.auth import auth_bp
from app.routes.buddies import buddies_bp
from app.routes.challenges import challenges_bp
from app.routes.groups import groups_bp
from app.routes.health import health_bp
from app.routes.social import social_bp
from app.routes.users import users_bp


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
        message_queue=None if app.testing else app.config.get("REDIS_URL"),
    )

    @jwt.unauthorized_loader
    def _missing_token(reason: str):
        return jsonify({"error": f"Authentification requise ({reason})."}), 401

    @jwt.invalid_token_loader
    def _invalid_token(reason: str):
        return jsonify({"error": f"Jeton JWT invalide ({reason})."}), 401

    @jwt.expired_token_loader
    def _expired_token(_jwt_header: dict, _jwt_payload: dict):
        return jsonify({"error": "Jeton JWT expire."}), 401

    @app.get("/uploads/<path:filename>")
    def serve_uploaded_media(filename: str):
        """Sert les avatars et medias stockes sur le volume persistant."""
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(buddies_bp)
    return app
