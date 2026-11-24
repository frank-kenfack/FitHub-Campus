"""Tests automatises de l'Etape 3 : Stories Workouts, Photos Avant/Apres, Likes & Commentaires."""

import io
import os
import uuid

import pytest
from PIL import Image

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Campus, SportGroup, Story, User, Workout
from app.seed import seed_database
from app.services.media_storage import remove_uploaded_file


def _make_png_bytes(color: tuple[int, int, int] = (230, 26, 95)) -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", (480, 360), color=color).save(buf, format="PNG")
    buf.seek(0)
    return buf


@pytest.fixture()
def app():
    """Fournit l'instance Flask de test et nettoie toutes les donnees temporaires."""
    application = create_app(TestingConfig)
    created_emails: list[str] = []
    created_story_ids: list[int] = []
    created_group_ids: list[int] = []

    with application.app_context():
        seed_database()
        application.config["_TEST_EMAILS"] = created_emails
        application.config["_TEST_STORY_IDS"] = created_story_ids
        application.config["_TEST_GROUP_IDS"] = created_group_ids
        yield application

        upload_folder = application.config["UPLOAD_FOLDER"]
        for sid in created_story_ids:
            st = db.session.get(Story, sid)
            if st is not None:
                for url in (st.media_url, st.before_media_url, st.after_media_url):
                    if url:
                        remove_uploaded_file(url, upload_folder)
                wk = db.session.get(Workout, st.workout_id) if st.workout_id else None
                db.session.delete(st)
                if wk is not None:
                    db.session.delete(wk)

        for gid in created_group_ids:
            grp = db.session.get(SportGroup, gid)
            if grp is not None:
                db.session.delete(grp)

        for email in created_emails:
            usr = User.query.filter_by(email=email).first()
            if usr is not None:
                db.session.delete(usr)

        db.session.commit()


@pytest.fixture()
def client(app):
    """Client HTTP de test."""
    return app.test_client()


def _register_user(app, client, suffix: str = "") -> tuple[dict, str]:
    tag = f"{uuid.uuid4().hex[:8]}{suffix}"
    email = f"social_{tag}@campus.fr"
    campus = Campus.query.order_by(Campus.id.asc()).first()
    app.config["_TEST_EMAILS"].append(email)
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": f"soc_{tag}",
            "password": "StrongPassword99!",
            "campus_id": campus.id,
        },
    )
    assert res.status_code == 201
    response_payload = res.get_json()
    return response_payload["user"], response_payload["access_token"]


def test_create_workout_story_and_24h_feed(app, client):
    """US-3.1 : Publication d'une story workout avec image valide, Workout lie et filtre 24h."""
    user, token = _register_user(app, client, "_w1")

    res = client.post(
        "/api/social/stories",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "sport": "Running",
            "duration_minutes": "42",
            "calories": "480",
            "distance_km": "8.5",
            "title": "Footing Matinal Parc",
            "caption": "Tres bonnes sensations ce matin !",
            "visibility": "public",
            "image": (_make_png_bytes(), "workout.png"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 201, res.get_json()
    post = res.get_json()["post"]
    app.config["_TEST_STORY_IDS"].append(post["id"])

    assert post["kind"] == "workout_story"
    assert post["media_url"].startswith("/uploads/stories/")
    assert post["workout"]["sport"] == "Running"
    assert post["workout"]["duration_minutes"] == 42
    assert post["workout"]["distance_km"] == 8.5
    assert post["is_fresh_24h"] is True

    # Verifie la presence du fichier sur disque et le gain XP (+25)
    rel = post["media_url"].removeprefix("/uploads/")
    assert os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], rel))
    refreshed_user = db.session.get(User, user["id"])
    assert refreshed_user.xp_points == 25

    # Verifie la presence dans le filtre 24h
    feed_24h = client.get("/api/social/posts?timeframe=24h").get_json()
    ids_24h = [p["id"] for p in feed_24h["posts"]]
    assert post["id"] in ids_24h


def test_workout_story_rejects_invalid_payload(app, client):
    """US-3.1 : Rejette une duree invalide ou un fichier non-image."""
    _, token = _register_user(app, client, "_bad")

    bad_duration = client.post(
        "/api/social/stories",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "sport": "Running",
            "duration_minutes": "0",
            "image": (_make_png_bytes(), "ok.png"),
        },
        content_type="multipart/form-data",
    )
    assert bad_duration.status_code == 400

    bad_file = client.post(
        "/api/social/stories",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "sport": "Running",
            "duration_minutes": "30",
            "image": (io.BytesIO(b"pas une image"), "fake.png"),
        },
        content_type="multipart/form-data",
    )
    assert bad_file.status_code == 400


def test_create_before_after_dual_upload(app, client):
    """US-3.2 : Double upload Avant/Apres fonctionnel et images accessibles en HTTP."""
    _, token = _register_user(app, client, "_ba")

    res = client.post(
        "/api/social/before-after",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Evolution Gainage & Pompe",
            "duration_label": "8 semaines",
            "caption": "Entrainement regulier 4x par semaine.",
            "visibility": "public",
            "before_image": (_make_png_bytes((90, 90, 120)), "avant.png"),
            "after_image": (_make_png_bytes((27, 138, 61)), "apres.png"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 201, res.get_json()
    post = res.get_json()["post"]
    app.config["_TEST_STORY_IDS"].append(post["id"])

    assert post["kind"] == "before_after"
    assert post["title"] == "Evolution Gainage & Pompe"
    assert post["duration_label"] == "8 semaines"
    assert post["before_media_url"] != post["after_media_url"]

    for media_url in (post["before_media_url"], post["after_media_url"]):
        r = client.get(media_url)
        assert r.status_code == 200
        assert r.mimetype == "image/png"
        r.close()


def test_group_visibility_restricts_access_to_members(app, client):
    """US-3.2 : Un post en visibilite 'group' n'est visible que par les membres du groupe."""
    _, token_member = _register_user(app, client, "_vis1")
    _, token_outsider = _register_user(app, client, "_vis2")

    grp_res = client.post(
        "/api/groups",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"name": "Groupe Prive Social Test", "sport": "Boxe"},
    )
    gid = grp_res.get_json()["group"]["id"]
    app.config["_TEST_GROUP_IDS"].append(gid)

    post_res = client.post(
        "/api/social/stories",
        headers={"Authorization": f"Bearer {token_member}"},
        data={
            "sport": "Boxe",
            "duration_minutes": "50",
            "visibility": "group",
            "group_id": str(gid),
            "caption": "Sparring interne au club",
            "image": (_make_png_bytes(), "boxe.png"),
        },
        content_type="multipart/form-data",
    )
    assert post_res.status_code == 201
    pid = post_res.get_json()["post"]["id"]
    app.config["_TEST_STORY_IDS"].append(pid)

    # Visible pour le membre
    member_feed = client.get(
        "/api/social/posts",
        headers={"Authorization": f"Bearer {token_member}"},
    ).get_json()["posts"]
    assert pid in [p["id"] for p in member_feed]

    # Invisible pour un non-membre ou visiteur anonyme
    outsider_feed = client.get(
        "/api/social/posts",
        headers={"Authorization": f"Bearer {token_outsider}"},
    ).get_json()["posts"]
    assert pid not in [p["id"] for p in outsider_feed]

    anon_feed = client.get("/api/social/posts").get_json()["posts"]
    assert pid not in [p["id"] for p in anon_feed]


def test_delete_post_author_only_and_removes_files(app, client):
    """US-3.2 : Seul l'auteur peut supprimer son post, et les fichiers sont nettoyes."""
    _, token_author = _register_user(app, client, "_del1")
    _, token_other = _register_user(app, client, "_del2")

    res = client.post(
        "/api/social/before-after",
        headers={"Authorization": f"Bearer {token_author}"},
        data={
            "title": "Post A Supprimer",
            "duration_label": "4 semaines",
            "before_image": (_make_png_bytes((40, 40, 40)), "b.png"),
            "after_image": (_make_png_bytes((200, 50, 80)), "a.png"),
        },
        content_type="multipart/form-data",
    )
    post = res.get_json()["post"]
    pid = post["id"]
    app.config["_TEST_STORY_IDS"].append(pid)

    before_disk = os.path.join(
        app.config["UPLOAD_FOLDER"],
        post["before_media_url"].removeprefix("/uploads/"),
    )
    after_disk = os.path.join(
        app.config["UPLOAD_FOLDER"],
        post["after_media_url"].removeprefix("/uploads/"),
    )
    assert os.path.isfile(before_disk) and os.path.isfile(after_disk)

    # Refus 403 pour un autre utilisateur
    forbidden = client.delete(
        f"/api/social/posts/{pid}",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert forbidden.status_code == 403

    # Suppression 200 pour l'auteur + nettoyage disque
    ok_del = client.delete(
        f"/api/social/posts/{pid}",
        headers={"Authorization": f"Bearer {token_author}"},
    )
    assert ok_del.status_code == 200
    assert not os.path.isfile(before_disk)
    assert not os.path.isfile(after_disk)


def test_like_toggle_and_idempotence(app, client):
    """US-3.3 : Toggle et actions explicites like/unlike sont strictement idempotents."""
    _, token = _register_user(app, client, "_like")
    res = client.post(
        "/api/social/stories",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "sport": "Fitness",
            "duration_minutes": "35",
            "image": (_make_png_bytes(), "fit.png"),
        },
        content_type="multipart/form-data",
    )
    pid = res.get_json()["post"]["id"]
    app.config["_TEST_STORY_IDS"].append(pid)

    # Toggle -> True (1)
    r1 = client.post(
        f"/api/social/posts/{pid}/like",
        headers={"Authorization": f"Bearer {token}"},
    ).get_json()
    assert r1["liked"] is True and r1["likes_count"] == 1

    # Appel explicite 'like' une 2e fois -> toujours 1 (idempotent)
    r2 = client.post(
        f"/api/social/posts/{pid}/like",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "like"},
    ).get_json()
    assert r2["liked"] is True and r2["likes_count"] == 1

    # Toggle -> False (0)
    r3 = client.post(
        f"/api/social/posts/{pid}/like",
        headers={"Authorization": f"Bearer {token}"},
    ).get_json()
    assert r3["liked"] is False and r3["likes_count"] == 0


def test_comments_crud_and_authorization(app, client):
    """US-3.3 : Ajout, lecture et controle des droits de suppression d'un commentaire."""
    _, token_post_owner = _register_user(app, client, "_c1")
    _, token_commenter = _register_user(app, client, "_c2")
    _, token_stranger = _register_user(app, client, "_c3")

    res = client.post(
        "/api/social/stories",
        headers={"Authorization": f"Bearer {token_post_owner}"},
        data={
            "sport": "Cyclisme",
            "duration_minutes": "75",
            "image": (_make_png_bytes(), "velo.png"),
        },
        content_type="multipart/form-data",
    )
    pid = res.get_json()["post"]["id"]
    app.config["_TEST_STORY_IDS"].append(pid)

    c_res = client.post(
        f"/api/social/posts/{pid}/comments",
        headers={"Authorization": f"Bearer {token_commenter}"},
        json={"content": "Super sortie velo !"},
    )
    assert c_res.status_code == 201
    cid = c_res.get_json()["comment"]["id"]
    assert c_res.get_json()["comments_count"] == 1

    listed = client.get(f"/api/social/posts/{pid}/comments").get_json()["comments"]
    assert len(listed) == 1 and listed[0]["content"] == "Super sortie velo !"

    # Un tiers ne peut pas supprimer -> 403
    assert (
        client.delete(
            f"/api/social/comments/{cid}",
            headers={"Authorization": f"Bearer {token_stranger}"},
        ).status_code
        == 403
    )

    # L'auteur du commentaire peut supprimer -> 200
    del_res = client.delete(
        f"/api/social/comments/{cid}",
        headers={"Authorization": f"Bearer {token_commenter}"},
    )
    assert del_res.status_code == 200
    assert del_res.get_json()["comments_count"] == 0


def test_unauthenticated_social_mutations_return_401(client):
    """US-3.1..3.3 : Toutes les ecritures sociales exigent un JWT valide."""
    assert client.post("/api/social/stories").status_code == 401
    assert client.post("/api/social/before-after").status_code == 401
    assert client.post("/api/social/posts/1/like").status_code == 401
    assert (
        client.post("/api/social/posts/1/comments", json={"content": "hi"}).status_code
        == 401
    )
