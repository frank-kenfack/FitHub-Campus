"""Tests de validation de l'Etape 1 : socle Docker, BDD, seed et sante API."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Badge, Campus, PlaceEvent, User
from app.seed import seed_database

EXPECTED_TABLES = {
    "campuses",
    "users",
    "groups",
    "group_members",
    "workouts",
    "stories",
    "story_likes",
    "story_comments",
    "challenges",
    "challenge_entries",
    "fit_buddies",
    "encouragements",
    "places_events",
    "event_rsvps",
    "badges",
    "user_badges",
}


@pytest.fixture()
def app():
    """Fournit l'application Flask configuree pour les tests."""
    application = create_app(TestingConfig)
    with application.app_context():
        seed_database()
        yield application


@pytest.fixture()
def client(app):
    """Client HTTP Flask pour tester les endpoints."""
    return app.test_client()


def test_health_endpoint_ok(client):
    """GET /api/health retourne 200 avec PostgreSQL et Redis operationnels."""
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["redis"] == "ok"


def test_all_mvp_tables_created(app):
    """Toutes les 16 tables du modele MVP sont presentes dans PostgreSQL."""
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - existing_tables
    assert not missing, f"Tables manquantes : {missing}"


def test_seed_is_idempotent(app):
    """Executer seed_database() plusieurs fois ne cree aucun doublon."""
    seed_database()
    seed_database()
    assert Campus.query.count() == 4
    assert Badge.query.count() == 5
    assert PlaceEvent.query.count() == 4


def test_campuses_endpoint_returns_seeded_data(client):
    response = client.get("/api/campuses")
    assert response.status_code == 200
    campuses_payload = response.get_json()
    assert len(campuses_payload["campuses"]) == 4
    first = campuses_payload["campuses"][0]
    assert {"id", "name", "city", "latitude", "longitude"} <= set(first.keys())


def test_foreign_key_integrity_enforced(app):
    """La base PostgreSQL rejette un utilisateur rattache a un campus inexistant."""
    invalid_user = User(
        email="invalid_fk@campus.fr",
        username="invalid_fk_user",
        password_hash="fakehash",
        campus_id=999999,
    )
    db.session.add(invalid_user)
    try:
        with pytest.raises(IntegrityError):
            db.session.commit()
    finally:
        db.session.rollback()
