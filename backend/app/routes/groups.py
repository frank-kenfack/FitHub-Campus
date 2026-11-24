"""Routes des groupes sportifs etudiants."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Campus, GroupMember, SportGroup, User
from app.services.domain_serializers import serialize_group

groups_bp = Blueprint("groups", __name__, url_prefix="/api/groups")


def _optional_user_id() -> int | None:
    raw = get_jwt_identity()
    return int(raw) if raw is not None else None


@groups_bp.get("")
@jwt_required(optional=True)
def list_groups():
    query = SportGroup.query
    campus_id = request.args.get("campus_id", type=int)
    sport = (request.args.get("sport") or "").strip()
    search = (request.args.get("q") or "").strip()

    if campus_id is not None:
        query = query.filter(SportGroup.campus_id == campus_id)
    if sport:
        query = query.filter(SportGroup.sport.ilike(f"%{sport}%"))
    if search:
        query = query.filter(
            db.or_(
                SportGroup.name.ilike(f"%{search}%"),
                SportGroup.description.ilike(f"%{search}%"),
            )
        )

    groups = query.order_by(SportGroup.created_at.desc(), SportGroup.id.desc()).all()
    uid = _optional_user_id()
    return jsonify({"groups": [serialize_group(g, current_user_id=uid) for g in groups]}), 200


@groups_bp.get("/<int:group_id>")
@jwt_required(optional=True)
def get_group_detail(group_id: int):
    group = db.session.get(SportGroup, group_id)
    if group is None:
        return jsonify({"error": "Groupe sportif introuvable."}), 404
    uid = _optional_user_id()
    return (
        jsonify(
            {
                "group": serialize_group(
                    group,
                    current_user_id=uid,
                    include_members=True,
                )
            }
        ),
        200,
    )


@groups_bp.post("")
@jwt_required()
def create_group():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    request_body = request.get_json(silent=True) or {}
    name = (request_body.get("name") or "").strip()
    sport = (request_body.get("sport") or "").strip()
    description = (request_body.get("description") or "").strip()
    campus_id = request_body.get("campus_id", user.campus_id)

    if len(name) < 3 or len(name) > 120:
        return jsonify({"error": "Le nom du groupe doit faire entre 3 et 120 caracteres."}), 400
    if len(sport) < 2 or len(sport) > 60:
        return jsonify({"error": "La discipline sportive est requise."}), 400
    if not isinstance(campus_id, int) or db.session.get(Campus, campus_id) is None:
        return jsonify({"error": "Campus selectionne introuvable."}), 400

    group = SportGroup(
        name=name,
        sport=sport,
        description=description[:600],
        campus_id=campus_id,
        created_by=user.id,
    )
    db.session.add(group)
    db.session.flush()

    membership = GroupMember(group_id=group.id, user_id=user.id, role="admin")
    db.session.add(membership)
    db.session.commit()

    return (
        jsonify(
            {
                "group": serialize_group(
                    group,
                    current_user_id=user.id,
                    include_members=True,
                )
            }
        ),
        201,
    )


@groups_bp.put("/<int:group_id>")
@jwt_required()
def update_group(group_id: int):
    uid = int(get_jwt_identity())
    group = db.session.get(SportGroup, group_id)
    if group is None:
        return jsonify({"error": "Groupe sportif introuvable."}), 404
    if group.created_by != uid:
        return jsonify({"error": "Seul le createur du groupe peut le modifier."}), 403

    request_body = request.get_json(silent=True) or {}
    if "name" in request_body:
        name = (request_body.get("name") or "").strip()
        if len(name) < 3 or len(name) > 120:
            return jsonify({"error": "Nom de groupe invalide."}), 400
        group.name = name
    if "sport" in request_body:
        sport = (request_body.get("sport") or "").strip()
        if len(sport) < 2 or len(sport) > 60:
            return jsonify({"error": "Discipline invalide."}), 400
        group.sport = sport
    if "description" in request_body:
        group.description = (request_body.get("description") or "").strip()[:600]
    if "campus_id" in request_body:
        campus_id = request_body.get("campus_id")
        if not isinstance(campus_id, int) or db.session.get(Campus, campus_id) is None:
            return jsonify({"error": "Campus introuvable."}), 400
        group.campus_id = campus_id

    db.session.commit()
    return (
        jsonify(
            {
                "group": serialize_group(
                    group,
                    current_user_id=uid,
                    include_members=True,
                )
            }
        ),
        200,
    )


@groups_bp.delete("/<int:group_id>")
@jwt_required()
def delete_group(group_id: int):
    uid = int(get_jwt_identity())
    group = db.session.get(SportGroup, group_id)
    if group is None:
        return jsonify({"error": "Groupe sportif introuvable."}), 404
    if group.created_by != uid:
        return jsonify({"error": "Seul le createur du groupe peut le supprimer."}), 403

    db.session.delete(group)
    db.session.commit()
    return jsonify({"deleted": True, "group_id": group_id}), 200


@groups_bp.post("/<int:group_id>/join")
@jwt_required()
def join_group(group_id: int):
    uid = int(get_jwt_identity())
    group = db.session.get(SportGroup, group_id)
    if group is None:
        return jsonify({"error": "Groupe sportif introuvable."}), 404

    existing = GroupMember.query.filter_by(group_id=group.id, user_id=uid).first()
    if existing is None:
        db.session.add(GroupMember(group_id=group.id, user_id=uid, role="member"))
        db.session.commit()

    return (
        jsonify(
            {
                "joined": True,
                "group": serialize_group(
                    group,
                    current_user_id=uid,
                    include_members=True,
                ),
            }
        ),
        200,
    )


@groups_bp.post("/<int:group_id>/leave")
@jwt_required()
def leave_group(group_id: int):
    uid = int(get_jwt_identity())
    group = db.session.get(SportGroup, group_id)
    if group is None:
        return jsonify({"error": "Groupe sportif introuvable."}), 404

    membership = GroupMember.query.filter_by(group_id=group.id, user_id=uid).first()
    if membership is not None:
        db.session.delete(membership)
        db.session.commit()

    return (
        jsonify(
            {
                "joined": False,
                "group": serialize_group(
                    group,
                    current_user_id=uid,
                    include_members=True,
                ),
            }
        ),
        200,
    )
