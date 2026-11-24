"""Routes d'authentification JWT."""

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Campus, User
from app.services.domain_serializers import serialize_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


@auth_bp.post("/register")
def register():
    request_body = request.get_json(silent=True) or {}
    email = (request_body.get("email") or "").strip().lower()
    username = (request_body.get("username") or "").strip()
    password = request_body.get("password") or ""
    campus_id = request_body.get("campus_id")

    if not email or "@" not in email:
        return jsonify({"error": "Adresse email invalide."}), 400
    if len(username) < 2 or len(username) > 60:
        return jsonify({"error": "Le pseudo doit contenir entre 2 et 60 caracteres."}), 400
    if len(password) < 8:
        return jsonify({"error": "Le mot de passe doit contenir au moins 8 caracteres."}), 400
    if not isinstance(campus_id, int) or db.session.get(Campus, campus_id) is None:
        return jsonify({"error": "Campus selectionne introuvable."}), 400

    if User.query.filter_by(email=email).first() is not None:
        return jsonify({"error": "Cet email est deja utilise."}), 409
    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"error": "Ce pseudo est deja pris."}), 409

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        campus_id=campus_id,
        bio=(request_body.get("bio") or "").strip(),
        favorite_sports=(request_body.get("favorite_sports") or "Fitness").strip() or "Fitness",
        level=(request_body.get("level") or "Intermediaire").strip() or "Intermediaire",
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return (
        jsonify(
            {
                "access_token": token,
                "user": serialize_user(user, include_stats=True),
            }
        ),
        201,
    )


@auth_bp.post("/login")
def login():
    request_body = request.get_json(silent=True) or {}
    email = (request_body.get("email") or "").strip().lower()
    password = request_body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not verify_password(password, user.password_hash):
        return jsonify({"error": "Identifiants invalides."}), 401

    token = create_access_token(identity=str(user.id))
    return (
        jsonify(
            {
                "access_token": token,
                "user": serialize_user(user, include_stats=True),
            }
        ),
        200,
    )


@auth_bp.get("/me")
@jwt_required()
def get_session_user():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401
    return jsonify({"user": serialize_user(user, include_stats=True)}), 200
