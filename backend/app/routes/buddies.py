"""Routes Fit-Buddy (matching, demandes et historique des encouragements)."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, socketio
from app.models import Campus, Encouragement, FitBuddy, User
from app.services.buddy_matching import (
    create_and_emit_encouragement,
    find_buddy_relation,
    serialize_buddy_relation,
    serialize_encouragement,
)

buddies_bp = Blueprint("buddies", __name__, url_prefix="/api/buddies")


def _sports_tokens(sports_str: str) -> set[str]:
    return {
        tok.strip().lower()
        for tok in (sports_str or "").replace("/", ",").split(",")
        if tok.strip()
    }


def _compatibility_score(me: User, candidate: User) -> int:
    score = 15
    if me.campus_id == candidate.campus_id:
        score += 45
    common_sports = _sports_tokens(me.favorite_sports) & _sports_tokens(
        candidate.favorite_sports
    )
    if common_sports:
        score += min(25, 15 + 10 * (len(common_sports) - 1))
    if (me.level or "").lower() == (candidate.level or "").lower():
        score += 15
    return min(100, score)


@buddies_bp.get("/discover")
@jwt_required()
def discover_buddies():
    me = db.session.get(User, int(get_jwt_identity()))
    if me is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    campus_id = request.args.get("campus_id", type=int)
    sport = (request.args.get("sport") or "").strip()
    level = (request.args.get("level") or "").strip()
    search = (request.args.get("q") or "").strip()

    query = User.query.filter(User.id != me.id)
    if campus_id is not None:
        query = query.filter(User.campus_id == campus_id)
    if sport:
        query = query.filter(User.favorite_sports.ilike(f"%{sport}%"))
    if level:
        query = query.filter(User.level.ilike(f"%{level}%"))
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f"%{search}%"),
                User.bio.ilike(f"%{search}%"),
            )
        )

    candidates = query.all()
    matched_candidates = []
    for cand in candidates:
        rel = find_buddy_relation(me.id, cand.id)
        rel_status = "none"
        rel_id = None
        if rel is not None:
            rel_id = rel.id
            if rel.status == "pending":
                rel_status = (
                    "pending_sent" if rel.requester_id == me.id else "pending_received"
                )
            else:
                rel_status = rel.status

        campus = db.session.get(Campus, cand.campus_id)
        matched_candidates.append(
            {
                "id": cand.id,
                "username": cand.username,
                "avatar_url": cand.avatar_url,
                "campus_id": cand.campus_id,
                "campus_name": campus.name if campus else "",
                "favorite_sports": cand.favorite_sports,
                "level": cand.level,
                "bio": cand.bio,
                "xp_points": cand.xp_points,
                "compatibility_score": _compatibility_score(me, cand),
                "relation_status": rel_status,
                "relation_id": rel_id,
            }
        )

    matched_candidates.sort(key=lambda item: (-item["compatibility_score"], item["username"]))
    return jsonify({"candidates": matched_candidates}), 200


@buddies_bp.get("")
@jwt_required()
def list_my_buddies():
    uid = int(get_jwt_identity())
    relations = (
        FitBuddy.query.filter(
            db.or_(FitBuddy.requester_id == uid, FitBuddy.addressee_id == uid)
        )
        .order_by(FitBuddy.created_at.desc(), FitBuddy.id.desc())
        .all()
    )

    accepted = []
    incoming_pending = []
    outgoing_pending = []

    for rel in relations:
        serialized = serialize_buddy_relation(rel, current_user_id=uid)
        if rel.status == "accepted":
            accepted.append(serialized)
        elif rel.status == "pending":
            if rel.addressee_id == uid:
                incoming_pending.append(serialized)
            else:
                outgoing_pending.append(serialized)

    return (
        jsonify(
            {
                "accepted": accepted,
                "incoming_pending": incoming_pending,
                "outgoing_pending": outgoing_pending,
            }
        ),
        200,
    )


@buddies_bp.post("/request")
@jwt_required()
def send_buddy_request():
    uid = int(get_jwt_identity())
    request_body = request.get_json(silent=True) or {}
    addressee_id = request_body.get("addressee_id")

    if not isinstance(addressee_id, int) or addressee_id <= 0:
        return jsonify({"error": "Identifiant destinataire invalide."}), 400
    if addressee_id == uid:
        return jsonify({"error": "Impossible de s'envoyer une demande a soi-meme."}), 400

    target = db.session.get(User, addressee_id)
    if target is None:
        return jsonify({"error": "Etudiant destinataire introuvable."}), 404

    existing = find_buddy_relation(uid, addressee_id)
    if existing is not None:
        if existing.status in {"pending", "accepted"}:
            return jsonify({"error": "Une demande ou relation Fit-Buddy existe deja."}), 409
        existing.requester_id = uid
        existing.addressee_id = addressee_id
        existing.status = "pending"
        db.session.commit()
        rel = existing
    else:
        rel = FitBuddy(requester_id=uid, addressee_id=addressee_id, status="pending")
        db.session.add(rel)
        db.session.commit()

    socketio.emit(
        "buddy_request",
        serialize_buddy_relation(rel, current_user_id=addressee_id),
        to=f"user_{addressee_id}",
    )
    return jsonify({"relation": serialize_buddy_relation(rel, current_user_id=uid)}), 201


@buddies_bp.post("/<int:relation_id>/respond")
@jwt_required()
def respond_buddy_request(relation_id: int):
    uid = int(get_jwt_identity())
    rel = db.session.get(FitBuddy, relation_id)
    if rel is None:
        return jsonify({"error": "Demande Fit-Buddy introuvable."}), 404
    if rel.addressee_id != uid:
        return jsonify({"error": "Seul le destinataire peut repondre a cette demande."}), 403
    if rel.status != "pending":
        return jsonify({"error": "Cette demande a deja ete traitee."}), 400

    request_body = request.get_json(silent=True) or {}
    decision = (request_body.get("decision") or "").strip().lower()
    if decision not in {"accept", "decline"}:
        return jsonify({"error": "Decision invalide ('accept' ou 'decline' attendu)."}), 400

    if decision == "accept":
        rel.status = "accepted"
        requester = db.session.get(User, rel.requester_id)
        addressee = db.session.get(User, rel.addressee_id)
        if requester:
            requester.xp_points = (requester.xp_points or 0) + 25
        if addressee:
            addressee.xp_points = (addressee.xp_points or 0) + 25
    else:
        rel.status = "declined"

    db.session.commit()

    socketio.emit(
        "buddy_updated",
        serialize_buddy_relation(rel, current_user_id=rel.requester_id),
        to=f"user_{rel.requester_id}",
    )
    return jsonify({"relation": serialize_buddy_relation(rel, current_user_id=uid)}), 200


@buddies_bp.get("/<int:partner_id>/encouragements")
@jwt_required()
def list_encouragements(partner_id: int):
    uid = int(get_jwt_identity())
    rel = find_buddy_relation(uid, partner_id)
    if rel is None or rel.status != "accepted":
        return jsonify({"error": "Relation Fit-Buddy active requise."}), 403

    rows = (
        Encouragement.query.filter(
            db.or_(
                db.and_(
                    Encouragement.sender_id == uid,
                    Encouragement.receiver_id == partner_id,
                ),
                db.and_(
                    Encouragement.sender_id == partner_id,
                    Encouragement.receiver_id == uid,
                ),
            )
        )
        .order_by(Encouragement.created_at.asc(), Encouragement.id.asc())
        .all()
    )
    return (
        jsonify(
            {
                "encouragements": [serialize_encouragement(e) for e in rows],
                "streak_days": serialize_buddy_relation(rel, current_user_id=uid)[
                    "streak_days"
                ],
            }
        ),
        200,
    )


@buddies_bp.post("/<int:partner_id>/encouragements")
@jwt_required()
def post_encouragement(partner_id: int):
    uid = int(get_jwt_identity())
    request_body = request.get_json(silent=True) or {}
    payload, err, status_code = create_and_emit_encouragement(
        sender_id=uid,
        receiver_id=partner_id,
        raw_message=str(request_body.get("message") or ""),
    )
    if err:
        return jsonify({"error": err}), status_code
    return jsonify({"encouragement": payload}), status_code
