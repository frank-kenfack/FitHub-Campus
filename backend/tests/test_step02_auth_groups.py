"""Tests automatises de l'Etape 2 : Auth JWT, Profils, Avatars et Groupes."""

import io
import os
import uuid

import pytest
from PIL import Image

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Campus, SportGroup, User
from app.seed import seed_database
from app.utils.media import remove_uploaded_file


@pytest.fixture()
def app():
    """Fournit l'application Flask de test et nettoie les entites temporaires."""
    application = create_app(TestingConfig)
    created_emails: list[str] = []
    created_group_ids: list[int] = []

    with application.app_context():
        seed_database()
        application.config["_TEST_EMAILS"] = created_emails
        application.config["_TEST_GROUP_IDS"] = created_group_ids
        yield application

        for gid in created_group_ids:
            grp = db.session.get(SportGroup, gid)
            if grp is not None:
                db.session.delete(grp)

        for email in created_emails:
            usr = User.query.filter_by(email=email).first()
            if usr is not None:
                if usr.avatar_url:
                    remove_uploaded_file(
                        usr.avatar_url,
                        application.config["UPLOAD_FOLDER"],
                    )
                db.session.delete(usr)
        db.session.commit()


@pytest.fixture()
def client(app):
    """Client HTTP Flask pour les tests d'integration."""
    return app.test_client()


def _register_temp_user(app, client, suffix: str = "") -> tuple[dict, str]:
    """Cree un etudiant temporaire unique et retourne (user_dict, token)."""
    tag = f"{uuid.uuid4().hex[:8]}{suffix}"
    email = f"test_{tag}@campus.fr"
    campus = Campus.query.order_by(Campus.id.asc()).first()
    app.config["_TEST_EMAILS"].append(email)

    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": f"user_{tag}",
            "password": "StrongPassword99!",
            "campus_id": campus.id,
            "favorite_sports": "Running, Natation",
            "level": "Debutant",
        },
    )
    assert res.status_code == 201, res.get_json()
    body = res.get_json()
    return body["user"], body["access_token"]


def test_register_hashes_password_and_returns_jwt(app, client):
    """US-2.1 : L'inscription hache le mot de passe en bcrypt et renvoie un JWT."""
    user_json, token = _register_temp_user(app, client)
    assert token
    assert "password" not in user_json
    assert "password_hash" not in user_json

    db_user = User.query.filter_by(email=user_json["email"]).first()
    assert db_user is not None
    assert db_user.password_hash != "StrongPassword99!"
    assert db_user.password_hash.startswith("$2b$")


def test_register_validation_and_duplicates(app, client):
    """US-2.1 : Rejette mot de passe trop court, campus inconnu et email doublon."""
    user_json, _ = _register_temp_user(app, client)
    campus = Campus.query.first()

    # Doublon d'email -> 409
    dup = client.post(
        "/api/auth/register",
        json={
            "email": user_json["email"],
            "username": f"other_{uuid.uuid4().hex[:6]}",
            "password": "StrongPassword99!",
            "campus_id": campus.id,
        },
    )
    assert dup.status_code == 409

    # Mot de passe trop court -> 400
    short_pw = client.post(
        "/api/auth/register",
        json={
            "email": f"short_{uuid.uuid4().hex[:6]}@campus.fr",
            "username": f"short_{uuid.uuid4().hex[:6]}",
            "password": "123",
            "campus_id": campus.id,
        },
    )
    assert short_pw.status_code == 400

    # Campus inexistant -> 400
    bad_campus = client.post(
        "/api/auth/register",
        json={
            "email": f"nocampus_{uuid.uuid4().hex[:6]}@campus.fr",
            "username": f"nocampus_{uuid.uuid4().hex[:6]}",
            "password": "StrongPassword99!",
            "campus_id": 999999,
        },
    )
    assert bad_campus.status_code == 400


def test_login_success_and_invalid_credentials(app, client):
    """US-2.1 : Connexion valide renvoie 200+JWT ; mauvais mot de passe renvoie 401."""
    user_json, _ = _register_temp_user(app, client)

    ok_res = client.post(
        "/api/auth/login",
        json={"email": user_json["email"], "password": "StrongPassword99!"},
    )
    assert ok_res.status_code == 200
    assert "access_token" in ok_res.get_json()

    ko_res = client.post(
        "/api/auth/login",
        json={"email": user_json["email"], "password": "WrongPassword!"},
    )
    assert ko_res.status_code == 401


def test_protected_routes_return_401_without_valid_jwt(client):
    """US-2.1 : Les routes privees renvoient 401 sans jeton ou avec jeton falsifie."""
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/users/me").status_code == 401
    assert client.put("/api/users/me", json={"bio": "test"}).status_code == 401
    assert client.post("/api/groups", json={"name": "Test", "sport": "Run"}).status_code == 401

    forged = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer jeton.invalide.falsifie"},
    )
    assert forged.status_code == 401


def test_profile_update_and_personal_stats(app, client):
    """US-2.2 : Edition du profil persistee en BDD et lecture des statistiques."""
    _, token = _register_temp_user(app, client)
    campuses = Campus.query.order_by(Campus.id.asc()).all()
    new_campus = campuses[-1]

    upd = client.put(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "bio": "Preparation marathon inter-ecoles",
            "favorite_sports": "Running, Cyclisme",
            "level": "Avance",
            "campus_id": new_campus.id,
        },
    )
    assert upd.status_code == 200

    me = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    profile = me.get_json()["user"]
    assert profile["bio"] == "Preparation marathon inter-ecoles"
    assert profile["favorite_sports"] == "Running, Cyclisme"
    assert profile["level"] == "Avance"
    assert profile["campus_id"] == new_campus.id
    assert {"workouts_count", "groups_count", "badges_count", "xp_points"} <= set(
        profile["stats"].keys()
    )


def test_avatar_upload_saved_on_volume_and_served(app, client):
    """US-2.2 : Upload d'avatar PNG valide sur volume persistant et servi en HTTP."""
    _, token = _register_temp_user(app, client)

    img_buf = io.BytesIO()
    Image.new("RGB", (600, 600), color=(230, 26, 95)).save(img_buf, format="PNG")
    img_buf.seek(0)

    res = client.post(
        "/api/users/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        data={"avatar": (img_buf, "mon_avatar.png")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    avatar_url = res.get_json()["user"]["avatar_url"]
    assert avatar_url.startswith("/uploads/avatars/")

    rel_file = avatar_url.removeprefix("/uploads/")
    disk_path = os.path.join(app.config["UPLOAD_FOLDER"], rel_file)
    assert os.path.isfile(disk_path)

    served = client.get(avatar_url)
    assert served.status_code == 200
    assert served.mimetype == "image/png"
    served.close()


def test_avatar_upload_rejects_invalid_file(app, client):
    """US-2.2 : Un fichier texte deguise en image est rejete avec un code 400."""
    _, token = _register_temp_user(app, client)
    fake_buf = io.BytesIO(b"ceci n est pas une image")

    res = client.post(
        "/api/users/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        data={"avatar": (fake_buf, "malicious.png")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400


def test_groups_crud_permissions_and_filters(app, client):
    """US-2.3 : Creation, filtrage campus/sport, modification et controle createur."""
    _, token_owner = _register_temp_user(app, client, "_owner")
    _, token_other = _register_temp_user(app, client, "_other")
    campus = Campus.query.order_by(Campus.id.asc()).first()

    create_res = client.post(
        "/api/groups",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={
            "name": "Club Escalade Test B3",
            "sport": "Escalade",
            "description": "Bloc et voie tous les mercredis soir.",
            "campus_id": campus.id,
        },
    )
    assert create_res.status_code == 201
    group = create_res.get_json()["group"]
    gid = group["id"]
    app.config["_TEST_GROUP_IDS"].append(gid)
    assert group["members_count"] == 1
    assert group["is_member"] is True

    # Filtrage par sport et campus
    filtered = client.get(f"/api/groups?campus_id={campus.id}&sport=Escalade")
    assert filtered.status_code == 200
    ids = [g["id"] for g in filtered.get_json()["groups"]]
    assert gid in ids

    # Modification interdite a un non-createur -> 403
    forbidden_upd = client.put(
        f"/api/groups/{gid}",
        headers={"Authorization": f"Bearer {token_other}"},
        json={"description": "Tentative non autorisee"},
    )
    assert forbidden_upd.status_code == 403

    # Modification autorisee au createur -> 200
    ok_upd = client.put(
        f"/api/groups/{gid}",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"description": "Nouvelle description officielle."},
    )
    assert ok_upd.status_code == 200
    assert ok_upd.get_json()["group"]["description"] == "Nouvelle description officielle."

    # Suppression interdite au non-createur -> 403, autorisee au createur -> 200
    assert (
        client.delete(
            f"/api/groups/{gid}",
            headers={"Authorization": f"Bearer {token_other}"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/groups/{gid}",
            headers={"Authorization": f"Bearer {token_owner}"},
        ).status_code
        == 200
    )


def test_group_join_leave_and_member_listing(app, client):
    """US-2.3 : Rejoindre et quitter un groupe met a jour la liste des membres."""
    _, token_owner = _register_temp_user(app, client, "_g1")
    user_member, token_member = _register_temp_user(app, client, "_g2")

    create_res = client.post(
        "/api/groups",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={
            "name": "Natation Matinale Test",
            "sport": "Natation",
            "description": "Longueurs a 7h30 avant les TP.",
        },
    )
    gid = create_res.get_json()["group"]["id"]
    app.config["_TEST_GROUP_IDS"].append(gid)

    # Adherer au groupe (et verifier l'idempotence d'un second appel)
    join_res = client.post(
        f"/api/groups/{gid}/join",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert join_res.status_code == 200
    assert join_res.get_json()["group"]["members_count"] == 2
    assert join_res.get_json()["group"]["is_member"] is True

    join_again = client.post(
        f"/api/groups/{gid}/join",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert join_again.status_code == 200
    assert join_again.get_json()["group"]["members_count"] == 2

    # Verifier la presence dans le detail des membres
    detail = client.get(f"/api/groups/{gid}").get_json()["group"]
    usernames = [m["username"] for m in detail["members"]]
    assert user_member["username"] in usernames

    # Quitter le groupe
    leave_res = client.post(
        f"/api/groups/{gid}/leave",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert leave_res.status_code == 200
    assert leave_res.get_json()["group"]["members_count"] == 1
    assert leave_res.get_json()["group"]["is_member"] is False
