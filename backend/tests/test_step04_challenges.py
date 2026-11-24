"""Tests automatises de l'Etape 4 : Defis Inter-Campus, Scores & Classements."""

import io
import os
import uuid

import pytest
from PIL import Image

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Campus, Challenge, ChallengeEntry, User, Workout
from app.seed import seed_database
from app.services.media_storage import remove_uploaded_file


def _make_png() -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), color=(27, 138, 61)).save(buf, format="PNG")
    buf.seek(0)
    return buf


@pytest.fixture()
def app():
    """Instance Flask de test avec nettoyage automatique des defis et comptes."""
    application = create_app(TestingConfig)
    created_emails: list[str] = []
    created_challenge_ids: list[int] = []

    with application.app_context():
        seed_database()
        application.config["_TEST_EMAILS"] = created_emails
        application.config["_TEST_CHALLENGE_IDS"] = created_challenge_ids
        yield application

        upload_folder = application.config["UPLOAD_FOLDER"]
        for cid in created_challenge_ids:
            ch = db.session.get(Challenge, cid)
            if ch is not None:
                for entry in ChallengeEntry.query.filter_by(challenge_id=cid).all():
                    if entry.proof_media_url:
                        remove_uploaded_file(entry.proof_media_url, upload_folder)
                db.session.delete(ch)

        for email in created_emails:
            usr = User.query.filter_by(email=email).first()
            if usr is not None:
                Workout.query.filter_by(user_id=usr.id).delete()
                db.session.delete(usr)

        db.session.commit()


@pytest.fixture()
def client(app):
    """Client HTTP Flask."""
    return app.test_client()


def _register_on_campus(app, client, campus_id: int, suffix: str = "") -> tuple[dict, str]:
    tag = f"{uuid.uuid4().hex[:8]}{suffix}"
    email = f"defi_{tag}@campus.fr"
    app.config["_TEST_EMAILS"].append(email)
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": f"ch_{tag}",
            "password": "StrongPassword99!",
            "campus_id": campus_id,
        },
    )
    assert res.status_code == 201
    body = res.get_json()
    return body["user"], body["access_token"]


def test_create_and_filter_active_vs_completed_challenges(app, client):
    """US-4.1 : Creation d'un defi actif et verification des filtres active / completed."""
    campus = Campus.query.order_by(Campus.id.asc()).first()
    _, token = _register_on_campus(app, client, campus.id, "_c1")

    res = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Defi 100 km Cyclisme Campus",
            "description": "Aller en cours a velo toute la semaine.",
            "sport": "Cyclisme",
            "target_value": 100,
            "unit": "km",
            "duration_days": 7,
        },
    )
    assert res.status_code == 201, res.get_json()
    created = res.get_json()["challenge"]
    app.config["_TEST_CHALLENGE_IDS"].append(created["id"])
    assert created["is_active"] is True
    assert created["is_joined"] is True
    assert created["participants_count"] == 1

    active_ids = [
        c["id"] for c in client.get("/api/challenges?status=active").get_json()["challenges"]
    ]
    completed_list = client.get("/api/challenges?status=completed").get_json()["challenges"]
    completed_ids = [c["id"] for c in completed_list]

    assert created["id"] in active_ids
    assert created["id"] not in completed_ids
    assert len(completed_list) >= 1
    assert all(c["is_active"] is False for c in completed_list)


def test_join_challenge_attaches_campus_and_prevents_duplicates(app, client):
    """US-4.1 : L'inscription rattache l'utilisateur a son campus et bloque les doublons (409)."""
    campuses = Campus.query.order_by(Campus.id.asc()).all()
    _, token_creator = _register_on_campus(app, client, campuses[0].id, "_jc1")
    user_joiner, token_joiner = _register_on_campus(app, client, campuses[1].id, "_jc2")

    ch_id = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {token_creator}"},
        json={
            "title": "Defi Anti Doublon",
            "sport": "Running",
            "target_value": 50,
            "unit": "km",
            "duration_days": 5,
        },
    ).get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(ch_id)

    join_ok = client.post(
        f"/api/challenges/{ch_id}/join",
        headers={"Authorization": f"Bearer {token_joiner}"},
    )
    assert join_ok.status_code == 201
    entry = ChallengeEntry.query.filter_by(
        challenge_id=ch_id,
        user_id=user_joiner["id"],
    ).first()
    assert entry is not None
    assert entry.campus_id == campuses[1].id

    # Deuxieme inscription refusee en 409
    join_dup = client.post(
        f"/api/challenges/{ch_id}/join",
        headers={"Authorization": f"Bearer {token_joiner}"},
    )
    assert join_dup.status_code == 409


def test_submit_performance_accumulates_individual_and_campus_scores(app, client):
    """US-4.2 : Les performances s'additionnent exactement par etudiant et par campus."""
    campuses = Campus.query.order_by(Campus.id.asc()).all()
    same_campus = campuses[0]
    _, tok_a = _register_on_campus(app, client, same_campus.id, "_pa")
    _, tok_b = _register_on_campus(app, client, same_campus.id, "_pb")

    ch_id = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={
            "title": "Defi Cumul Campus",
            "sport": "Running",
            "target_value": 100,
            "unit": "km",
        },
    ).get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(ch_id)

    client.post(
        f"/api/challenges/{ch_id}/join",
        headers={"Authorization": f"Bearer {tok_b}"},
    )

    # Etudiant A soumet 10.5 puis 4.5 (= 15.0) ; Etudiant B soumet 10.0 -> total campus = 25.0
    client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"value": 10.5},
    )
    client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"value": 4.5},
    )
    res_b = client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {tok_b}"},
        json={"value": 10.0},
    )
    assert res_b.status_code == 200
    lb = res_b.get_json()

    assert lb["challenge"]["total_score"] == 25.0
    top_campus = lb["campus_leaderboard"][0]
    assert top_campus["campus_id"] == same_campus.id
    assert top_campus["total_score"] == 25.0


def test_submit_performance_with_optional_photo_proof(app, client):
    """US-4.2 : Preuve photo optionnelle validee, stockee et servie en HTTP 200."""
    campus = Campus.query.first()
    _, token = _register_on_campus(app, client, campus.id, "_proof")

    ch_id = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Defi Preuve Photo",
            "sport": "Natation",
            "target_value": 20,
            "unit": "km",
        },
    ).get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(ch_id)

    perf_res = client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {token}"},
        data={"value": "2.5", "proof_image": (_make_png(), "montre_gps.png")},
        content_type="multipart/form-data",
    )
    assert perf_res.status_code == 200
    proof_url = perf_res.get_json()["challenge"]["my_proof_url"]
    assert proof_url.startswith("/uploads/proofs/")

    rel = proof_url.removeprefix("/uploads/")
    assert os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], rel))

    served = client.get(proof_url)
    assert served.status_code == 200
    assert served.mimetype == "image/png"
    served.close()


def test_submit_performance_strict_validation_and_membership_gate(app, client):
    """US-4.2 : Rejette valeur <= 0, valeur plafonnee irrealiste et non-participant (403)."""
    campus = Campus.query.first()
    _, tok_owner = _register_on_campus(app, client, campus.id, "_val1")
    _, tok_outsider = _register_on_campus(app, client, campus.id, "_val2")

    ch_id = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {tok_owner}"},
        json={
            "title": "Defi Validation Stricte",
            "sport": "Running",
            "target_value": 50,
            "unit": "km",
        },
    ).get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(ch_id)

    # Valeur <= 0 -> 400
    assert (
        client.post(
            f"/api/challenges/{ch_id}/performances",
            headers={"Authorization": f"Bearer {tok_owner}"},
            json={"value": 0},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/challenges/{ch_id}/performances",
            headers={"Authorization": f"Bearer {tok_owner}"},
            json={"value": -12},
        ).status_code
        == 400
    )

    # Valeur > plafond raisonnable (max(50*2, 5000) = 5000) -> 400
    assert (
        client.post(
            f"/api/challenges/{ch_id}/performances",
            headers={"Authorization": f"Bearer {tok_owner}"},
            json={"value": 99999},
        ).status_code
        == 400
    )

    # Utilisateur non inscrit -> 403
    assert (
        client.post(
            f"/api/challenges/{ch_id}/performances",
            headers={"Authorization": f"Bearer {tok_outsider}"},
            json={"value": 5},
        ).status_code
        == 403
    )


def test_challenge_leaderboard_descending_order_and_my_rank(app, client):
    """US-4.3 : Podium tri decroissant fiable, top 3 identifie et rang personnel retourne."""
    campuses = Campus.query.order_by(Campus.id.asc()).all()
    _, tok_1 = _register_on_campus(app, client, campuses[0].id, "_lb1")
    user_2, tok_2 = _register_on_campus(app, client, campuses[1].id, "_lb2")
    _, tok_3 = _register_on_campus(app, client, campuses[2].id, "_lb3")

    ch_id = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {tok_1}"},
        json={
            "title": "Defi Podium Test",
            "sport": "Cross-Training",
            "target_value": 300,
            "unit": "reps",
        },
    ).get_json()["challenge"]["id"]
    app.config["_TEST_CHALLENGE_IDS"].append(ch_id)

    client.post(f"/api/challenges/{ch_id}/join", headers={"Authorization": f"Bearer {tok_2}"})
    client.post(f"/api/challenges/{ch_id}/join", headers={"Authorization": f"Bearer {tok_3}"})

    # Scores : tok_3 = 90 (1er), tok_2 = 60 (2e), tok_1 = 30 (3e)
    client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {tok_1}"},
        json={"value": 30},
    )
    client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {tok_2}"},
        json={"value": 60},
    )
    client.post(
        f"/api/challenges/{ch_id}/performances",
        headers={"Authorization": f"Bearer {tok_3}"},
        json={"value": 90},
    )

    lb = client.get(
        f"/api/challenges/{ch_id}/leaderboard",
        headers={"Authorization": f"Bearer {tok_2}"},
    ).get_json()

    indiv = lb["individual_leaderboard"]
    assert [row["score"] for row in indiv] == [90.0, 60.0, 30.0]
    assert [row["rank"] for row in indiv] == [1, 2, 3]
    assert all(row["is_podium"] is True for row in indiv)
    assert lb["my_rank"] == 2
    assert indiv[1]["user_id"] == user_2["id"] and indiv[1]["is_me"] is True

    campus_scores = [row["total_score"] for row in lb["campus_leaderboard"]]
    assert campus_scores == sorted(campus_scores, reverse=True)
    assert lb["my_campus_rank"] == 2


def test_global_leaderboard_campus_and_individuals(app, client):
    """US-4.3 : Le classement general retourne les 4 campus tries et le rang de l'etudiant."""
    campus = Campus.query.first()
    _, token = _register_on_campus(app, client, campus.id, "_glob")

    res = client.get(
        "/api/challenges/leaderboard/global",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert len(body["campus_leaderboard"]) == 4
    xp_list = [c["total_xp"] for c in body["campus_leaderboard"]]
    assert xp_list == sorted(xp_list, reverse=True)
    assert body["my_rank"] is not None
    assert body["my_campus_rank"] in {1, 2, 3, 4}


def test_unauthenticated_challenge_mutations_return_401(client):
    """US-4.1..4.2 : Creation, inscription et soumission exigent un JWT valide."""
    assert client.post("/api/challenges", json={"title": "Test"}).status_code == 401
    assert client.post("/api/challenges/1/join").status_code == 401
    assert (
        client.post("/api/challenges/1/performances", json={"value": 5}).status_code
        == 401
    )
