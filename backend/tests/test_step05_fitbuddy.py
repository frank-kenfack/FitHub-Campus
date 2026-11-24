"""Tests automatises de l'Etape 5 : Fit-Buddy Matching, WebSockets Temps Reel & Streak."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db, socketio
from app.models import Campus, Encouragement, FitBuddy, User, Workout
from app.seed import seed_database


@pytest.fixture()
def app():
    """Fournit l'instance Flask de test et nettoie les relations/messages crees."""
    application = create_app(TestingConfig)
    created_emails: list[str] = []

    with application.app_context():
        seed_database()
        application.config["_TEST_EMAILS"] = created_emails
        yield application

        for email in created_emails:
            usr = User.query.filter_by(email=email).first()
            if usr is not None:
                Encouragement.query.filter(
                    db.or_(
                        Encouragement.sender_id == usr.id,
                        Encouragement.receiver_id == usr.id,
                    )
                ).delete()
                FitBuddy.query.filter(
                    db.or_(
                        FitBuddy.requester_id == usr.id,
                        FitBuddy.addressee_id == usr.id,
                    )
                ).delete()
                Workout.query.filter_by(user_id=usr.id).delete()
                db.session.delete(usr)
        db.session.commit()


@pytest.fixture()
def client(app):
    """Client HTTP de test."""
    return app.test_client()


def _register_student(
    app,
    client,
    campus_id: int,
    sports: str = "Running",
    level: str = "Intermediaire",
    suffix: str = "",
) -> tuple[dict, str]:
    tag = f"{uuid.uuid4().hex[:8]}{suffix}"
    email = f"buddy_{tag}@campus.fr"
    app.config["_TEST_EMAILS"].append(email)
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": f"fb_{tag}",
            "password": "StrongPassword99!",
            "campus_id": campus_id,
            "favorite_sports": sports,
            "level": level,
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    return body["user"], body["access_token"]


def test_discover_buddies_filters_and_compatibility_score(app, client):
    """US-5.1 : Filtrage par campus/sport/niveau et calcul du score d'affinite."""
    campuses = Campus.query.order_by(Campus.id.asc()).all()
    c_same, c_other = campuses[0], campuses[1]

    _, tok_me = _register_student(
        app, client, c_same.id, sports="Escalade, Yoga", level="Avance", suffix="_m1"
    )
    u_twin, _ = _register_student(
        app, client, c_same.id, sports="Escalade", level="Avance", suffix="_m2"
    )
    u_far, _ = _register_student(
        app, client, c_other.id, sports="Natation", level="Debutant", suffix="_m3"
    )

    res = client.get(
        f"/api/buddies/discover?campus_id={c_same.id}&sport=Escalade&level=Avance",
        headers={"Authorization": f"Bearer {tok_me}"},
    )
    assert res.status_code == 200
    cands = res.get_json()["candidates"]
    ids = [c["id"] for c in cands]
    assert u_twin["id"] in ids
    assert u_far["id"] not in ids

    twin_entry = next(c for c in cands if c["id"] == u_twin["id"])
    assert twin_entry["compatibility_score"] >= 85


def test_buddy_request_accept_and_decline_workflow(app, client):
    """US-5.1 : Cycle complet pending -> accept/decline, anti-doublon et controle destinataire."""
    campus = Campus.query.first()
    u_a, tok_a = _register_student(app, client, campus.id, suffix="_wa")
    u_b, tok_b = _register_student(app, client, campus.id, suffix="_wb")
    u_c, tok_c = _register_student(app, client, campus.id, suffix="_wc")

    # A envoie une demande a B -> 201 pending
    req_res = client.post(
        "/api/buddies/request",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"addressee_id": u_b["id"]},
    )
    assert req_res.status_code == 201
    rel_id = req_res.get_json()["relation"]["id"]
    assert req_res.get_json()["relation"]["status"] == "pending"

    # Doublon interdit -> 409
    assert (
        client.post(
            "/api/buddies/request",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"addressee_id": u_b["id"]},
        ).status_code
        == 409
    )

    # A (expediteur) ne peut pas auto-accepter sa propre demande -> 403
    assert (
        client.post(
            f"/api/buddies/{rel_id}/respond",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"decision": "accept"},
        ).status_code
        == 403
    )

    # B (destinataire) accepte -> 200 accepted (+25 XP chacun)
    acc_res = client.post(
        f"/api/buddies/{rel_id}/respond",
        headers={"Authorization": f"Bearer {tok_b}"},
        json={"decision": "accept"},
    )
    assert acc_res.status_code == 200
    assert acc_res.get_json()["relation"]["status"] == "accepted"

    # Verification d'un refus sur C -> status declined
    req_c = client.post(
        "/api/buddies/request",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"addressee_id": u_c["id"]},
    ).get_json()["relation"]["id"]
    dec_res = client.post(
        f"/api/buddies/{req_c}/respond",
        headers={"Authorization": f"Bearer {tok_c}"},
        json={"decision": "decline"},
    )
    assert dec_res.status_code == 200
    assert dec_res.get_json()["relation"]["status"] == "declined"


def test_realtime_websocket_delivery_between_two_sessions(app, client):
    """US-5.2 : Livraison instantanee via WebSocket entre 2 sessions connectees + historique BDD."""
    campus = Campus.query.first()
    u_a, tok_a = _register_student(app, client, campus.id, suffix="_wsa")
    u_b, tok_b = _register_student(app, client, campus.id, suffix="_wsb")

    rel_id = client.post(
        "/api/buddies/request",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"addressee_id": u_b["id"]},
    ).get_json()["relation"]["id"]
    client.post(
        f"/api/buddies/{rel_id}/respond",
        headers={"Authorization": f"Bearer {tok_b}"},
        json={"decision": "accept"},
    )

    # Ouverture simultanee de 2 sessions Socket.IO authentifiees
    ws_a = socketio.test_client(app, auth={"token": tok_a})
    ws_b = socketio.test_client(app, auth={"token": tok_b})
    assert ws_a.is_connected()
    assert ws_b.is_connected()

    # Vide les accusés de connexion initiaux
    ws_a.get_received()
    ws_b.get_received()

    # Session A envoie un encouragement temps reel a Session B
    ack = ws_a.emit(
        "send_encouragement",
        {"receiver_id": u_b["id"], "message": "Go training ! On se retrouve a 18h !"},
        callback=True,
    )
    assert ack["ok"] is True

    # Session B recoit instantanement l'evenement 'new_encouragement' sans polling
    received_b = ws_b.get_received()
    events_b = [pkt for pkt in received_b if pkt["name"] == "new_encouragement"]
    assert len(events_b) == 1
    msg_payload = events_b[0]["args"][0]
    assert msg_payload["sender_id"] == u_a["id"]
    assert msg_payload["receiver_id"] == u_b["id"]
    assert msg_payload["message"] == "Go training ! On se retrouve a 18h !"

    ws_a.disconnect()
    ws_b.disconnect()

    # Verification de la persistance de l'historique en BDD PostgreSQL
    hist = client.get(
        f"/api/buddies/{u_a['id']}/encouragements",
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert hist.status_code == 200
    messages = hist.get_json()["encouragements"]
    assert len(messages) == 1
    assert messages[0]["message"] == "Go training ! On se retrouve a 18h !"


def test_encouragement_blocked_if_not_accepted_buddies(app, client):
    """US-5.2 : Impossible d'envoyer un encouragement sans relation Fit-Buddy acceptee."""
    campus = Campus.query.first()
    _, tok_a = _register_student(app, client, campus.id, suffix="_blk1")
    u_stranger, _ = _register_student(app, client, campus.id, suffix="_blk2")

    res = client.post(
        f"/api/buddies/{u_stranger['id']}/encouragements",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"message": "Salut inconnu"},
    )
    assert res.status_code == 403

    ws_a = socketio.test_client(app, auth={"token": tok_a})
    ws_a.get_received()
    ack = ws_a.emit(
        "send_encouragement",
        {"receiver_id": u_stranger["id"], "message": "Test interdit"},
        callback=True,
    )
    assert ack["ok"] is False
    ws_a.disconnect()


def test_shared_streak_computed_from_consecutive_days(app, client):
    """US-5.3 : Le compteur de streak reflète les jours consecutifs d'activite du duo."""
    campus = Campus.query.first()
    u_a, tok_a = _register_student(app, client, campus.id, suffix="_st1")
    u_b, tok_b = _register_student(app, client, campus.id, suffix="_st2")

    rel_id = client.post(
        "/api/buddies/request",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"addressee_id": u_b["id"]},
    ).get_json()["relation"]["id"]
    client.post(
        f"/api/buddies/{rel_id}/respond",
        headers={"Authorization": f"Bearer {tok_b}"},
        json={"decision": "accept"},
    )

    now_utc = datetime.now(timezone.utc)
    db.session.add_all(
        [
            Workout(
                user_id=u_a["id"],
                sport="Running",
                duration_minutes=30,
                performed_at=now_utc - timedelta(days=2),
            ),
            Workout(
                user_id=u_b["id"],
                sport="Running",
                duration_minutes=35,
                performed_at=now_utc - timedelta(days=1),
            ),
            Workout(
                user_id=u_a["id"],
                sport="Running",
                duration_minutes=40,
                performed_at=now_utc,
            ),
        ]
    )
    db.session.commit()

    buddies_res = client.get(
        "/api/buddies",
        headers={"Authorization": f"Bearer {tok_a}"},
    ).get_json()
    assert len(buddies_res["accepted"]) == 1
    assert buddies_res["accepted"][0]["streak_days"] >= 3


def test_websocket_rejects_unauthenticated_or_forged_token(app):
    """US-5.2 : Une connexion Socket.IO sans JWT ou avec JWT falsifie est rejetee."""
    unauth_ws = socketio.test_client(app)
    assert not unauth_ws.is_connected()

    forged_ws = socketio.test_client(app, auth={"token": "jeton.invalide.xyz"})
    assert not forged_ws.is_connected()


def test_unauthenticated_buddy_routes_return_401(client):
    """US-5.1..5.3 : Toutes les routes Fit-Buddy exigent un JWT valide."""
    assert client.get("/api/buddies").status_code == 401
    assert client.get("/api/buddies/discover").status_code == 401
    assert client.post("/api/buddies/request", json={"addressee_id": 1}).status_code == 401
