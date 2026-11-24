"""Tests de l'Etape 7 : Recette End-to-End complete, Securite & Benchmark Latence (< 300 ms)."""

import io
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from app import create_app
from app.config import TestingConfig
from app.extensions import db, socketio
from app.models import (
    Campus,
    Challenge,
    Encouragement,
    EventRsvp,
    FitBuddy,
    PlaceEvent,
    SportGroup,
    Story,
    User,
    UserBadge,
    Workout,
)
from app.seed import seed_database
from app.services.media_storage import remove_uploaded_file


def _make_png(rgb: tuple[int, int, int] = (230, 26, 95)) -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", (320, 240), color=rgb).save(buf, format="PNG")
    buf.seek(0)
    return buf


@pytest.fixture()
def app():
    """Fournit l'instance Flask de test avec nettoyage complet apres recette E2E."""
    application = create_app(TestingConfig)
    created_emails: list[str] = []
    created_group_ids: list[int] = []
    created_story_ids: list[int] = []
    created_challenge_ids: list[int] = []
    created_place_ids: list[int] = []

    with application.app_context():
        seed_database()
        application.config["_TEST_EMAILS"] = created_emails
        application.config["_TEST_GROUP_IDS"] = created_group_ids
        application.config["_TEST_STORY_IDS"] = created_story_ids
        application.config["_TEST_CHALLENGE_IDS"] = created_challenge_ids
        application.config["_TEST_PLACE_IDS"] = created_place_ids
        yield application

        upload_folder = application.config["UPLOAD_FOLDER"]

        for sid in created_story_ids:
            st = db.session.get(Story, sid)
            if st is not None:
                for u in (st.media_url, st.before_media_url, st.after_media_url):
                    if u:
                        remove_uploaded_file(u, upload_folder)
                db.session.delete(st)

        for pid in created_place_ids:
            pl = db.session.get(PlaceEvent, pid)
            if pl is not None:
                db.session.delete(pl)

        for cid in created_challenge_ids:
            ch = db.session.get(Challenge, cid)
            if ch is not None:
                db.session.delete(ch)

        for gid in created_group_ids:
            grp = db.session.get(SportGroup, gid)
            if grp is not None:
                db.session.delete(grp)

        for email in created_emails:
            usr = User.query.filter_by(email=email).first()
            if usr is not None:
                if usr.avatar_url:
                    remove_uploaded_file(usr.avatar_url, upload_folder)
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
                EventRsvp.query.filter_by(user_id=usr.id).delete()
                UserBadge.query.filter_by(user_id=usr.id).delete()
                Workout.query.filter_by(user_id=usr.id).delete()
                db.session.delete(usr)

        db.session.commit()


@pytest.fixture()
def client(app):
    """Client HTTP Flask."""
    return app.test_client()


def _register(app, client, campus_id: int, suffix: str) -> tuple[dict, str]:
    tag = f"{uuid.uuid4().hex[:7]}{suffix}"
    email = f"e2e_{tag}@fithub.fr"
    app.config["_TEST_EMAILS"].append(email)
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": f"e2e_{tag}",
            "password": "StrongPassword99!",
            "campus_id": campus_id,
            "favorite_sports": "Running, Cross-Training",
            "level": "Avance",
        },
    )
    assert res.status_code == 201
    registration_payload = res.get_json()
    return registration_payload["user"], registration_payload["access_token"]


def test_complete_student_journey_end_to_end(app, client):
    """US-9.1 : Parcours E2E traversant les 6 modules fonctionnels jusqu'au 5/5 badges."""
    campuses = Campus.query.order_by(Campus.id.asc()).all()
    u_camille, tok_camille = _register(app, client, campuses[0].id, "_cam")
    u_yassine, tok_yassine = _register(app, client, campuses[1].id, "_yas")
    h_cam = {"Authorization": f"Bearer {tok_camille}"}
    h_yas = {"Authorization": f"Bearer {tok_yassine}"}

    # 1. Profil + Avatar
    assert (
        client.put(
            "/api/users/me",
            headers=h_cam,
            json={"bio": "Objectif 10 km campus", "level": "Avance"},
        ).status_code
        == 200
    )
    av_res = client.post(
        "/api/users/me/avatar",
        headers=h_cam,
        data={"avatar": (_make_png(), "avatar.png")},
        content_type="multipart/form-data",
    )
    assert av_res.status_code == 200

    # 2. Groupe sportif
    grp_res = client.post(
        "/api/groups",
        headers=h_cam,
        json={"name": "E2E Running Squad", "sport": "Running", "campus_id": campuses[0].id},
    )
    assert grp_res.status_code == 201
    gid = grp_res.get_json()["group"]["id"]
    app.config["_TEST_GROUP_IDS"].append(gid)
    assert client.post(f"/api/groups/{gid}/join", headers=h_yas).status_code == 200

    # 3. Story sociale + Like + Commentaire (1re seance)
    st_res = client.post(
        "/api/social/stories",
        headers=h_cam,
        data={
            "sport": "Running",
            "duration_minutes": "40",
            "distance_km": "7.2",
            "calories": "450",
            "title": "Sortie E2E",
            "visibility": "group",
            "group_id": str(gid),
            "image": (_make_png((27, 138, 61)), "run.png"),
        },
        content_type="multipart/form-data",
    )
    assert st_res.status_code == 201
    sid = st_res.get_json()["post"]["id"]
    app.config["_TEST_STORY_IDS"].append(sid)
    assert client.post(f"/api/social/posts/{sid}/like", headers=h_yas).status_code == 200
    assert (
        client.post(
            f"/api/social/posts/{sid}/comments",
            headers=h_yas,
            json={"content": "Top rythme E2E !"},
        ).status_code
        == 201
    )

    # 4. Defi inter-campus + performance (2e seance + badge top_campus)
    ch_res = client.post(
        "/api/challenges",
        headers=h_cam,
        json={
            "title": "Defi E2E Inter-Campus",
            "sport": "Running",
            "target_value": 80,
            "unit": "km",
            "duration_days": 5,
        },
    )
    assert ch_res.status_code == 201
    cid = ch_res.get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(cid)
    perf = client.post(
        f"/api/challenges/{cid}/performances",
        headers=h_cam,
        json={"value": 12.5},
    )
    assert perf.status_code == 200
    assert perf.get_json()["my_campus_rank"] == 1

    # 5. Fit-Buddy + Encouragement WebSocket temps reel (badge fit_buddy_solidarity)
    rel_id = client.post(
        "/api/buddies/request",
        headers=h_cam,
        json={"addressee_id": u_yassine["id"]},
    ).get_json()["relation"]["id"]
    assert (
        client.post(
            f"/api/buddies/{rel_id}/respond",
            headers=h_yas,
            json={"decision": "accept"},
        ).status_code
        == 200
    )
    ws_cam = socketio.test_client(app, auth={"token": tok_camille})
    ws_yas = socketio.test_client(app, auth={"token": tok_yassine})
    ws_cam.get_received()
    ws_yas.get_received()
    ack = ws_cam.emit(
        "send_encouragement",
        {"receiver_id": u_yassine["id"], "message": "Bravo Yassine pour le challenge E2E !"},
        callback=True,
    )
    assert ack["ok"] is True
    assert any(p["name"] == "new_encouragement" for p in ws_yas.get_received())
    ws_cam.disconnect()
    ws_yas.disconnect()

    # 6. Evenement geolocalise + RSVP (badge event_participant)
    ev_res = client.post(
        "/api/places/events",
        headers=h_cam,
        json={
            "title": "Footing E2E Campus",
            "sport": "Running",
            "campus_id": campuses[0].id,
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "max_participants": 8,
            "latitude": campuses[0].latitude,
            "longitude": campuses[0].longitude,
        },
    )
    assert ev_res.status_code == 201
    pid = ev_res.get_json()["place"]["id"]
    app.config["_TEST_PLACE_IDS"].append(pid)
    assert (
        client.post(f"/api/places/{pid}/rsvp", headers=h_yas, json={"action": "join"}).status_code
        == 200
    )

    # 7. Import de 3 activites supplementaires -> total >= 5 seances -> 5/5 badges debloques !
    imp_res = client.post(
        "/api/gamification/import-activity",
        headers=h_cam,
        json={
            "source": "google_fit",
            "challenge_id": cid,
            "activities": [
                {"sport": "Running", "duration_minutes": 32, "distance_km": 5.5},
                {"sport": "Cross-Training", "duration_minutes": 45, "distance_km": 0.0},
                {"sport": "Running", "duration_minutes": 50, "distance_km": 9.0},
            ],
        },
    )
    assert imp_res.status_code == 201
    summary = imp_res.get_json()["summary"]
    assert summary["unlocked_count"] == 5
    assert summary["total_badges"] == 5


def test_critical_api_endpoints_latency_under_300ms(app, client):
    """US-9.2 : Tous les endpoints critiques repondent en HTTP 200 en moins de 300 ms."""
    campus = Campus.query.order_by(Campus.id.asc()).first()
    _, token = _register(app, client, campus.id, "_perf")
    headers = {"Authorization": f"Bearer {token}"}

    # Appel de chauffe de la connexion SQLAlchemy/Redis
    client.get("/api/health")

    endpoints = [
        ("/api/health", None),
        ("/api/campuses", None),
        ("/api/users/me", headers),
        ("/api/groups", headers),
        ("/api/social/posts", headers),
        ("/api/challenges", headers),
        ("/api/challenges/leaderboard/global", headers),
        (f"/api/places?campus_id={campus.id}&radius_km=5", headers),
        ("/api/gamification/summary", headers),
    ]

    for path, hdrs in endpoints:
        t0 = time.perf_counter()
        res = client.get(path, headers=hdrs or {})
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200, f"{path} returned {res.status_code}"
        assert elapsed_ms < 300.0, f"Latence excessive sur {path} : {elapsed_ms:.1f} ms >= 300 ms"


def test_sql_injection_and_malicious_query_resilience(app, client):
    """US-9.2 : Les requetes SQLAlchemy parametrisees neutralisent toute tentative d'injection SQL."""
    campus = Campus.query.first()
    _, token = _register(app, client, campus.id, "_sqli")
    headers = {"Authorization": f"Bearer {token}"}

    users_before = User.query.count()
    sqli = "' OR 1=1; DROP TABLE users; --"

    assert client.get("/api/groups", query_string={"q": sqli, "sport": sqli}).status_code == 200
    assert client.get("/api/places", query_string={"sport": sqli}).status_code == 200
    assert (
        client.get("/api/buddies/discover", headers=headers, query_string={"q": sqli}).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": sqli, "password": "Password123!"},
        ).status_code
        == 401
    )
    assert User.query.count() == users_before


def test_cors_headers_and_json_404_error_contract(client):
    """US-9.2 : CORS actif sur /api/* et reponses d'erreur 404/405 structurees en JSON."""
    res = client.get("/api/health", headers={"Origin": "http://localhost:8080"})
    assert res.status_code == 200
    assert res.headers.get("Access-Control-Allow-Origin") in {"*", "http://localhost:8080"}

    missing = client.get("/api/endpoint-totalement-inconnu")
    assert missing.status_code == 404
    assert missing.is_json
    assert "error" in missing.get_json()

    wrong_method = client.delete("/api/health")
    assert wrong_method.status_code == 405
    assert wrong_method.is_json


def test_payload_boundary_and_nan_inf_rejection(app, client):
    """US-9.2 : Rejet propre en HTTP 400 des flottants NaN/Inf et valeurs hors bornes."""
    campus = Campus.query.first()
    _, token = _register(app, client, campus.id, "_nan")
    headers = {"Authorization": f"Bearer {token}"}

    # Rayon NaN ou negatif sur /api/places -> 400
    assert client.get(f"/api/places?campus_id={campus.id}&radius_km=nan").status_code == 400
    assert client.get(f"/api/places?campus_id={campus.id}&radius_km=-5").status_code == 400

    # Objectif Inf sur /api/challenges -> 400
    assert (
        client.post(
            "/api/challenges",
            headers=headers,
            json={
                "title": "Challenge Infini",
                "sport": "Running",
                "target_value": "Infinity",
                "unit": "km",
            },
        ).status_code
        == 400
    )


def test_health_reports_step07_and_consistent_counts(client):
    """US-9.1 : L'endpoint /api/health expose bien l'identifiant d'etape et les compteurs coherents."""
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"
    assert body["step"] in {"step-07/cicd-qualite-docs", "step-08/kubernetes-bonus"}
    assert body["stats"]["campuses"] == 4
    assert body["stats"]["badges"] == 5
