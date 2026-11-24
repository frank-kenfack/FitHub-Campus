"""Routes de gestion du profil etudiant et de l'avatar."""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Campus, User
from app.services.domain_serializers import serialize_user
from app.services.media_storage import remove_uploaded_file, save_validated_image

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.get("/me")
@jwt_required()
def get_my_profile():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401
    return jsonify({"user": serialize_user(user, include_stats=True)}), 200


@users_bp.put("/me")
@jwt_required()
def update_my_profile():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    request_body = request.get_json(silent=True) or {}

    if "username" in request_body:
        new_username = (request_body.get("username") or "").strip()
        if len(new_username) < 2 or len(new_username) > 60:
            return jsonify({"error": "Le pseudo doit contenir entre 2 et 60 caracteres."}), 400
        existing = User.query.filter(
            User.username == new_username,
            User.id != user.id,
        ).first()
        if existing is not None:
            return jsonify({"error": "Ce pseudo est deja pris."}), 409
        user.username = new_username

    if "campus_id" in request_body:
        campus_id = request_body.get("campus_id")
        if not isinstance(campus_id, int) or db.session.get(Campus, campus_id) is None:
            return jsonify({"error": "Campus selectionne introuvable."}), 400
        user.campus_id = campus_id

    if "bio" in request_body:
        user.bio = (request_body.get("bio") or "").strip()[:500]

    if "favorite_sports" in request_body:
        sports = (request_body.get("favorite_sports") or "").strip()
        if sports:
            user.favorite_sports = sports[:255]

    if "level" in request_body:
        level = (request_body.get("level") or "").strip()
        if level:
            user.level = level[:40]

    db.session.commit()
    return jsonify({"user": serialize_user(user, include_stats=True)}), 200


@users_bp.post("/me/avatar")
@jwt_required()
def upload_my_avatar():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    file_storage = request.files.get("avatar")
    try:
        new_url = save_validated_image(
            file_storage=file_storage,
            base_upload_folder=current_app.config["UPLOAD_FOLDER"],
            subfolder="avatars",
            max_size=(400, 400),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    old_avatar = user.avatar_url
    user.avatar_url = new_url
    db.session.commit()

    if old_avatar:
        remove_uploaded_file(old_avatar, current_app.config["UPLOAD_FOLDER"])

    return jsonify({"user": serialize_user(user, include_stats=True)}), 200


@users_bp.get("/<int:user_id>")
@jwt_required()
def get_public_profile(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "Etudiant introuvable."}), 404
    return jsonify({"user": serialize_user(user, include_stats=True)}), 200
