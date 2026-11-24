"""Tests automatises de l'Etape 6 : Geolocalisation Haversine, Evenements RSVP, Badges & Import GPX/Google Fit."""

import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    Campus,
    Challenge,
    Encouragement,
    EventRsvp,
    FitBuddy,
    PlaceEvent,
    User,
    UserBadge,
    Workout,
)
from app.seed import seed_database


@pytest.fixture()
def app():
    """Instance Flask de test nettoyant toutes les entites temporaires de l'Etape 6."""
    application = create_app(TestingConfig)
    created_emails: list[str] = []
    created_place_ids: list[int] = []
    created_challenge_ids: list[int] = []

    with application.app_context():
        seed_database()
        application.config["_TEST_EMAILS"] = created_emails
        application.config["_TEST_PLACE_IDS"] = created_place_ids
        application.config["_TEST_CHALLENGE_IDS"] = created_challenge_ids
        yield application

        for pid in created_place_ids:
            pl = db.session.get(PlaceEvent, pid)
            if pl is not None:
                db.session.delete(pl)

        for cid in created_challenge_ids:
            ch = db.session.get(Challenge, cid)
            if ch is not None:
                db.session.delete(ch)

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
                EventRsvp.query.filter_by(user_id=usr.id).delete()
                UserBadge.query.filter_by(user_id=usr.id).delete()
                Workout.query.filter_by(user_id=usr.id).delete()
                db.session.delete(usr)

        db.session.commit()


@pytest.fixture()
def client(app):
    """Client HTTP Flask."""
    return app.test_client()


def _register_student(app, client, campus_id: int, suffix: str = "") -> tuple[dict, str]:
    tag = f"{uuid.uuid4().hex[:8]}{suffix}"
    email = f"step6_{tag}@campus.fr"
    app.config["_TEST_EMAILS"].append(email)
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": f"geo_{tag}",
            "password": "StrongPassword99!",
            "campus_id": campus_id,
            "favorite_sports": "Running, Calisthenics",
            "level": "Intermediaire",
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    return body["user"], body["access_token"]


def test_haversine_radius_filtering_and_campus_fallback(app, client):
    """US-6.1 & US-6.3 : Filtrage exact par rayon Haversine, fallback campus et filtre sport/type."""
    lyon = Campus.query.filter_by(city="Lyon").first()
    assert lyon is not None

    # Rayon 2 km autour de Lyon Gerland -> inclut Halle Tony Garnier (~0.23 km), exclut Paris/Bordeaux/Lille
    near_res = client.get(
        f"/api/places?lat={lyon.latitude}&lon={lyon.longitude}&radius_km=2"
    )
    assert near_res.status_code == 200
    nearby_payload = near_res.get_json()
    assert nearby_payload["reference_point"]["source"] == "gps"
    titles = [p["title"] for p in nearby_payload["places"]]
    assert "Halle Sportive Tony Garnier Fit" in titles
    assert "Parc Street-Workout Vincennes" not in titles
    assert all(p["distance_km"] <= 2.0 for p in nearby_payload["places"])

    # Fallback automatique sur les coordonnees du campus si lat/lon absents
    fallback_res = client.get(f"/api/places?campus_id={lyon.id}&radius_km=2")
    assert fallback_res.status_code == 200
    assert fallback_res.get_json()["reference_point"]["source"] == "campus"
    assert len(fallback_res.get_json()["places"]) >= 1

    # Filtre combine type=spot & sport=Calisthenics -> Vincennes uniquement
    spot_res = client.get("/api/places?kind=spot&sport=Calisthenics")
    assert spot_res.status_code == 200
    spot_titles = [p["title"] for p in spot_res.get_json()["places"]]
    assert spot_titles == ["Parc Street-Workout Vincennes"]


def test_create_geolocated_event_and_rsvp_capacity_enforcement(app, client):
    """US-6.2 : Creation d'evenement geolocalise, RSVP et blocage strict au-dela de max_participants."""
    lyon = Campus.query.filter_by(city="Lyon").first()
    u1, tok1 = _register_student(app, client, lyon.id, "_ev1")
    _, tok2 = _register_student(app, client, lyon.id, "_ev2")
    _, tok3 = _register_student(app, client, lyon.id, "_ev3")

    starts_iso = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_res = client.post(
        "/api/places/events",
        headers={"Authorization": f"Bearer {tok1}"},
        json={
            "title": "Session Fractionne Parc Gerland",
            "sport": "Running",
            "campus_id": lyon.id,
            "starts_at": starts_iso,
            "max_participants": 2,
            "address": "Allee Pierre de Coubertin, Lyon",
            "latitude": 45.7265,
            "longitude": 4.8291,
        },
    )
    assert create_res.status_code == 201, create_res.get_json()
    body = create_res.get_json()
    ev = body["place"]
    ev_id = ev["id"]
    app.config["_TEST_PLACE_IDS"].append(ev_id)

    assert ev["kind"] == "event"
    assert ev["rsvp_count"] == 1
    assert ev["is_going"] is True
    assert ev["is_full"] is False
    unlocked_codes = [b["code"] for b in body["newly_unlocked_badges"]]
    assert "event_participant" in unlocked_codes

    # 2e participant rejoint -> 2/2 (complet)
    rsvp2 = client.post(
        f"/api/places/{ev_id}/rsvp",
        headers={"Authorization": f"Bearer {tok2}"},
        json={"action": "join"},
    )
    assert rsvp2.status_code == 200
    assert rsvp2.get_json()["place"]["rsvp_count"] == 2
    assert rsvp2.get_json()["place"]["is_full"] is True

    # 3e participant tente de rejoindre -> 409 Conflict
    rsvp3_blocked = client.post(
        f"/api/places/{ev_id}/rsvp",
        headers={"Authorization": f"Bearer {tok3}"},
        json={"action": "join"},
    )
    assert rsvp3_blocked.status_code == 409

    # 2e participant se desinscrit -> une place se libere pour le 3e
    leave2 = client.post(
        f"/api/places/{ev_id}/rsvp",
        headers={"Authorization": f"Bearer {tok2}"},
        json={"action": "leave"},
    )
    assert leave2.status_code == 200
    assert leave2.get_json()["place"]["rsvp_count"] == 1

    rsvp3_ok = client.post(
        f"/api/places/{ev_id}/rsvp",
        headers={"Authorization": f"Bearer {tok3}"},
        json={"action": "join"},
    )
    assert rsvp3_ok.status_code == 200
    assert rsvp3_ok.get_json()["place"]["rsvp_count"] == 2


def test_event_delete_restricted_to_organizer_and_protects_seeded_places(app, client):
    """US-6.2 : Seul l'organisateur peut supprimer son evenement ; les lieux partenaires sont proteges."""
    campus = Campus.query.first()
    _, tok_owner = _register_student(app, client, campus.id, "_do1")
    _, tok_other = _register_student(app, client, campus.id, "_do2")

    seeded_gym = PlaceEvent.query.filter(PlaceEvent.created_by.is_(None)).first()
    assert (
        client.delete(
            f"/api/places/{seeded_gym.id}",
            headers={"Authorization": f"Bearer {tok_owner}"},
        ).status_code
        == 403
    )

    ev_id = client.post(
        "/api/places/events",
        headers={"Authorization": f"Bearer {tok_owner}"},
        json={
            "title": "WOD Etudiant Test Suppression",
            "sport": "Cross-Training",
            "starts_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
            "max_participants": 10,
        },
    ).get_json()["place"]["id"]
    app.config["_TEST_PLACE_IDS"].append(ev_id)

    assert (
        client.delete(
            f"/api/places/{ev_id}",
            headers={"Authorization": f"Bearer {tok_other}"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/places/{ev_id}",
            headers={"Authorization": f"Bearer {tok_owner}"},
        ).status_code
        == 200
    )


def test_automatic_badges_unlocking_without_duplicates(app, client):
    """US-7.1 : Deblocage automatique sans doublon de first_workout, five_workouts et fit_buddy_solidarity."""
    campus = Campus.query.first()
    u_a, tok_a = _register_student(app, client, campus.id, "_bg1")
    u_b, tok_b = _register_student(app, client, campus.id, "_bg2")

    # Initialement 0 badge
    s0 = client.get(
        "/api/gamification/summary",
        headers={"Authorization": f"Bearer {tok_a}"},
    ).get_json()
    assert s0["unlocked_count"] == 0

    # 1re seance importee -> first_workout debloque
    imp1 = client.post(
        "/api/gamification/import-activity",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"sport": "Running", "duration_minutes": 30, "distance_km": 5.0},
    )
    assert imp1.status_code == 201
    assert "first_workout" in [b["code"] for b in imp1.get_json()["newly_unlocked_badges"]]

    # Appels repetes a summary -> aucun doublon en BDD
    client.get("/api/gamification/summary", headers={"Authorization": f"Bearer {tok_a}"})
    assert UserBadge.query.filter_by(user_id=u_a["id"]).count() == 1

    # 4 seances supplementaires (total = 5) -> five_workouts debloque
    imp_batch = client.post(
        "/api/gamification/import-activity",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={
            "activities": [
                {"sport": "Fitness", "duration_minutes": 25},
                {"sport": "Running", "duration_minutes": 35, "distance_km": 6.0},
                {"sport": "Musculation", "duration_minutes": 45},
                {"sport": "Cyclisme", "duration_minutes": 40, "distance_km": 12.0},
            ]
        },
    )
    assert imp_batch.status_code == 201
    assert "five_workouts" in [
        b["code"] for b in imp_batch.get_json()["newly_unlocked_badges"]
    ]

    # Encouragement Fit-Buddy -> fit_buddy_solidarity debloque
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
    client.post(
        f"/api/buddies/{u_b['id']}/encouragements",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"message": "Allez on lache rien pour le badge solidaire !"},
    )

    final_sum = client.get(
        "/api/gamification/summary",
        headers={"Authorization": f"Bearer {tok_a}"},
    ).get_json()
    unlocked_codes = {b["code"] for b in final_sum["badges"] if b["unlocked"]}
    assert {"first_workout", "five_workouts", "fit_buddy_solidarity"} <= unlocked_codes


def test_reward_tiers_and_xp_progression(app, client):
    """US-7.2 : Calcul exact des paliers de recompenses virtuelles et de la jauge XP."""
    campus = Campus.query.first()
    u, tok = _register_student(app, client, campus.id, "_tier")

    # Palier 1 : Athlete Bronze (0 XP)
    s_bronze = client.get(
        "/api/gamification/summary",
        headers={"Authorization": f"Bearer {tok}"},
    ).get_json()
    assert s_bronze["progression"]["current_tier"]["code"] == "bronze"
    assert s_bronze["progression"]["next_tier"]["code"] == "silver"

    # Passage au palier Legende Campus (>= 650 XP)
    db_user = db.session.get(User, u["id"])
    db_user.xp_points = 700
    db.session.commit()

    s_legend = client.get(
        "/api/gamification/summary",
        headers={"Authorization": f"Bearer {tok}"},
    ).get_json()
    assert s_legend["progression"]["current_tier"]["code"] == "legend"
    assert s_legend["progression"]["next_tier"] is None
    assert s_legend["progression"]["progress_pct"] == 100.0
    assert all(t["unlocked"] is True for t in s_legend["progression"]["tiers"])


def test_google_fit_json_import_credits_profile_and_active_challenge(app, client):
    """US-7.3 : L'import d'une session Google Fit credite le profil, le defi actif et le badge top_campus."""
    campus = Campus.query.first()
    _, tok = _register_student(app, client, campus.id, "_gfit")

    ch_id = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {tok}"},
        json={
            "title": "Defi Google Fit Sync 50 km",
            "sport": "Running",
            "target_value": 50,
            "unit": "km",
            "duration_days": 7,
        },
    ).get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(ch_id)

    now_ms = 1_760_000_000_000
    res = client.post(
        "/api/gamification/import-activity",
        headers={"Authorization": f"Bearer {tok}"},
        json={
            "source": "google_fit",
            "challenge_id": ch_id,
            "sessions": [
                {
                    "activityType": 8,
                    "startTimeMillis": now_ms,
                    "endTimeMillis": now_ms + 42 * 60_000,
                    "distanceMeters": 7800,
                    "calories": 495,
                }
            ],
        },
    )
    assert res.status_code == 201, res.get_json()
    payload = res.get_json()
    assert payload["imported_count"] == 1
    assert payload["imported_workouts"][0]["source"] == "google_fit"
    assert payload["imported_workouts"][0]["distance_km"] == 7.8
    assert payload["challenge_updates"][0]["challenge_id"] == ch_id
    assert payload["challenge_updates"][0]["new_score"] == 7.8

    unlocked_codes = {b["code"] for b in payload["newly_unlocked_badges"]}
    assert "first_workout" in unlocked_codes
    assert "top_campus" in unlocked_codes


def test_gpx_xml_upload_and_xxe_malformed_rejection(app, client):
    """US-7.3 : Import d'une trace XML .gpx par calcul Haversine et rejet securise des fichiers invalides."""
    campus = Campus.query.first()
    _, tok = _register_student(app, client, campus.id, "_gpx")

    valid_gpx = b"""<?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
      <trk>
        <type>Running</type>
        <trkseg>
          <trkpt lat="45.7299" lon="4.8273"><time>2026-11-24T08:00:00Z</time></trkpt>
          <trkpt lat="45.7479" lon="4.8273"><time>2026-11-24T08:12:00Z</time></trkpt>
          <trkpt lat="45.7659" lon="4.8273"><time>2026-11-24T08:25:00Z</time></trkpt>
        </trkseg>
      </trk>
    </gpx>"""

    ok_res = client.post(
        "/api/gamification/import-activity",
        headers={"Authorization": f"Bearer {tok}"},
        data={"file": (io.BytesIO(valid_gpx), "course_rhone.gpx")},
        content_type="multipart/form-data",
    )
    assert ok_res.status_code == 201, ok_res.get_json()
    w = ok_res.get_json()["imported_workouts"][0]
    assert w["source"] == "gpx"
    assert 3.8 <= w["distance_km"] <= 4.2
    assert w["duration_minutes"] == 25

    # Rejet XXE / DOCTYPE -> 400
    xxe_gpx = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe "test">]><gpx></gpx>'
    assert (
        client.post(
            "/api/gamification/import-activity",
            headers={"Authorization": f"Bearer {tok}"},
            data={"file": (io.BytesIO(xxe_gpx), "exploit.gpx")},
            content_type="multipart/form-data",
        ).status_code
        == 400
    )

    # Rejet extension non supportee -> 400
    assert (
        client.post(
            "/api/gamification/import-activity",
            headers={"Authorization": f"Bearer {tok}"},
            data={"file": (io.BytesIO(b"hello"), "notes.txt")},
            content_type="multipart/form-data",
        ).status_code
        == 400
    )


def test_unauthenticated_step06_mutations_return_401(client):
    """US-6.2 & US-7.1..7.3 : Les routes protegees de l'Etape 6 exigent un JWT valide."""
    assert client.post("/api/places/events", json={"title": "Test"}).status_code == 401
    assert client.post("/api/places/1/rsvp").status_code == 401
    assert client.get("/api/gamification/summary").status_code == 401
    assert (
        client.post(
            "/api/gamification/import-activity",
            json={"sport": "Running", "duration_minutes": 20},
        ).status_code
        == 401
    )
