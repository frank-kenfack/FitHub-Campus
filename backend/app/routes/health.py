"""Routes de sante et donnees de reference."""

import redis
from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.extensions import db
from app.models import (
    Badge,
    Campus,
    Challenge,
    FitBuddy,
    PlaceEvent,
    SportGroup,
    Story,
    User,
)

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def health_check():
    """Verifie la disponibilite de l'API, PostgreSQL et Redis."""
    checks = {"database": "error", "redis": "error"}
    stats = {
        "campuses": 0,
        "badges": 0,
        "places": 0,
        "users": 0,
        "groups": 0,
        "stories": 0,
        "challenges": 0,
        "buddies": 0,
    }

    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = "ok"
        stats = {
            "campuses": Campus.query.count(),
            "badges": Badge.query.count(),
            "places": PlaceEvent.query.count(),
            "users": User.query.count(),
            "groups": SportGroup.query.count(),
            "stories": Story.query.count(),
            "challenges": Challenge.query.count(),
            "buddies": FitBuddy.query.filter_by(status="accepted").count(),
        }
    except Exception as exc:  # pragma: no cover - remonte diagnostic sante
        checks["database_error"] = str(exc)

    try:
        client = redis.Redis.from_url(
            current_app.config["REDIS_URL"],
            socket_connect_timeout=2,
        )
        if client.ping():
            checks["redis"] = "ok"
    except Exception as exc:  # pragma: no cover - remonte diagnostic sante
        checks["redis_error"] = str(exc)

    healthy = checks["database"] == "ok" and checks["redis"] == "ok"
    status_code = 200 if healthy else 503
    return (
        jsonify(
            {
                "status": "ok" if healthy else "degraded",
                "service": "fithub-campus-api",
                "step": "step-07/cicd-qualite-docs",
                "checks": checks,
                "stats": stats,
            }
        ),
        status_code,
    )


@health_bp.get("/campuses")
def list_campuses():
    """Retourne la liste des campus etudiants disponibles."""
    campuses = Campus.query.order_by(Campus.name.asc()).all()
    return jsonify({"campuses": [c.to_dict() for c in campuses]}), 200
