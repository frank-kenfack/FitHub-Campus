"""Routes Defis Inter-Campus & Classements (Etape 4 : US-4.1, US-4.2, US-4.3)."""

import math
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import (
    Campus,
    Challenge,
    ChallengeEntry,
    SportGroup,
    User,
    Workout,
)
from app.utils.gamification import evaluate_and_award_badges
from app.utils.media import remove_uploaded_file, save_validated_image

challenges_bp = Blueprint("challenges", __name__, url_prefix="/api/challenges")


def _optional_uid() -> int | None:
    raw = get_jwt_identity()
    return int(raw) if raw is not None else None


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _is_challenge_active(challenge: Challenge, now_utc: datetime | None = None) -> bool:
    ref = now_utc or datetime.now(timezone.utc)
    ends_utc = _as_utc(challenge.ends_at)
    return bool(ends_utc and ends_utc >= ref)


def serialize_challenge(challenge: Challenge, current_user_id: int | None = None) -> dict:
    """Serialise un defi avec progression collective et statut de l'utilisateur."""
    now_utc = datetime.now(timezone.utc)
    entries = ChallengeEntry.query.filter_by(challenge_id=challenge.id).all()
    total_score = round(sum(e.score for e in entries), 2)
    target = float(challenge.target_value or 1.0)
    progress_pct = round(min(100.0, (total_score / target) * 100.0), 1) if target > 0 else 0.0

    my_entry = None
    if current_user_id:
        my_entry = next((e for e in entries if e.user_id == current_user_id), None)

    # Campus en tete sur ce defi
    campus_totals: dict[int, float] = {}
    for e in entries:
        campus_totals[e.campus_id] = campus_totals.get(e.campus_id, 0.0) + e.score
    top_campus_name = ""
    if campus_totals:
        best_cid = max(campus_totals.items(), key=lambda kv: kv[1])[0]
        best_campus = db.session.get(Campus, best_cid)
        if best_campus and campus_totals[best_cid] > 0:
            top_campus_name = best_campus.name

    creator = db.session.get(User, challenge.created_by)
    group = db.session.get(SportGroup, challenge.group_id) if challenge.group_id else None

    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "sport": challenge.sport,
        "target_value": challenge.target_value,
        "unit": challenge.unit,
        "starts_at": challenge.starts_at.isoformat() if challenge.starts_at else None,
        "ends_at": challenge.ends_at.isoformat() if challenge.ends_at else None,
        "is_active": _is_challenge_active(challenge, now_utc),
        "created_by": challenge.created_by,
        "creator_username": creator.username if creator else "Etudiant",
        "group_id": challenge.group_id,
        "group_name": group.name if group else "",
        "participants_count": len(entries),
        "total_score": total_score,
        "progress_pct": progress_pct,
        "top_campus_name": top_campus_name,
        "is_joined": my_entry is not None,
        "my_score": round(my_entry.score, 2) if my_entry else 0.0,
        "my_proof_url": my_entry.proof_media_url if my_entry else "",
    }


def _build_challenge_leaderboards(
    challenge: Challenge,
    current_user_id: int | None = None,
) -> dict:
    """Construit le classement inter-campus et le classement individuel d'un defi."""
    campuses = {c.id: c for c in Campus.query.all()}
    entries = (
        ChallengeEntry.query.filter_by(challenge_id=challenge.id)
        .order_by(ChallengeEntry.score.desc(), ChallengeEntry.id.asc())
        .all()
    )

    # 1. Agregation par campus (inclut aussi les campus a 0 pour visibilite inter-ecoles)
    campus_agg: dict[int, dict] = {
        cid: {
            "campus_id": cid,
            "campus_name": c.name,
            "city": c.city,
            "total_score": 0.0,
            "participants_count": 0,
        }
        for cid, c in campuses.items()
    }
    for entry in entries:
        bucket = campus_agg.get(entry.campus_id)
        if bucket is not None:
            bucket["total_score"] = round(bucket["total_score"] + entry.score, 2)
            bucket["participants_count"] += 1

    sorted_campuses = sorted(
        campus_agg.values(),
        key=lambda item: (-item["total_score"], -item["participants_count"], item["campus_name"]),
    )
    leader_campus_score = sorted_campuses[0]["total_score"] if sorted_campuses else 0.0

    my_user = db.session.get(User, current_user_id) if current_user_id else None
    my_campus_rank = None
    for idx, row in enumerate(sorted_campuses, start=1):
        row["rank"] = idx
        row["is_podium"] = idx <= 3
        row["gap_to_leader"] = round(max(0.0, leader_campus_score - row["total_score"]), 2)
        row["is_my_campus"] = bool(my_user and my_user.campus_id == row["campus_id"])
        if row["is_my_campus"]:
            my_campus_rank = idx

    # 2. Classement individuel des participants
    individuals = []
    my_rank = None
    leader_user_score = entries[0].score if entries else 0.0
    for idx, entry in enumerate(entries, start=1):
        usr = db.session.get(User, entry.user_id)
        cmp = campuses.get(entry.campus_id)
        is_me = bool(current_user_id and entry.user_id == current_user_id)
        if is_me:
            my_rank = idx
        individuals.append(
            {
                "rank": idx,
                "is_podium": idx <= 3,
                "user_id": entry.user_id,
                "username": usr.username if usr else "Etudiant",
                "avatar_url": usr.avatar_url if usr else "",
                "campus_id": entry.campus_id,
                "campus_name": cmp.name if cmp else "",
                "score": round(entry.score, 2),
                "gap_to_leader": round(max(0.0, leader_user_score - entry.score), 2),
                "proof_media_url": entry.proof_media_url,
                "is_me": is_me,
            }
        )

    return {
        "challenge": serialize_challenge(challenge, current_user_id=current_user_id),
        "campus_leaderboard": sorted_campuses,
        "individual_leaderboard": individuals,
        "my_rank": my_rank,
        "my_campus_rank": my_campus_rank,
    }


@challenges_bp.get("")
@jwt_required(optional=True)
def list_challenges():
    """Liste les defis inter-campus avec filtre actifs / termines / discipline (US-4.1)."""
    uid = _optional_uid()
    status_filter = (request.args.get("status") or "all").strip().lower()
    sport_filter = (request.args.get("sport") or "").strip()

    query = Challenge.query
    if sport_filter:
        query = query.filter(Challenge.sport.ilike(f"%{sport_filter}%"))

    now_utc = datetime.now(timezone.utc)
    if status_filter == "active":
        query = query.filter(Challenge.ends_at >= now_utc)
    elif status_filter == "completed":
        query = query.filter(Challenge.ends_at < now_utc)

    challenges = query.order_by(Challenge.ends_at.asc(), Challenge.id.desc()).all()
    return (
        jsonify(
            {
                "challenges": [
                    serialize_challenge(ch, current_user_id=uid) for ch in challenges
                ]
            }
        ),
        200,
    )


@challenges_bp.get("/leaderboard/global")
@jwt_required(optional=True)
def global_leaderboard():
    """Retourne le classement general inter-campus et individuel (US-4.3)."""
    uid = _optional_uid()
    my_user = db.session.get(User, uid) if uid else None
    campuses = Campus.query.all()

    # Cumul XP et participations defis par utilisateur
    entry_counts = dict(
        db.session.query(
            ChallengeEntry.user_id,
            func.count(ChallengeEntry.id),
        )
        .group_by(ChallengeEntry.user_id)
        .all()
    )

    users = User.query.order_by(User.xp_points.desc(), User.id.asc()).all()
    campus_scores: dict[int, dict] = {
        c.id: {
            "campus_id": c.id,
            "campus_name": c.name,
            "city": c.city,
            "total_xp": 0,
            "students_count": 0,
            "challenges_entries": 0,
        }
        for c in campuses
    }

    individuals = []
    my_rank = None
    top_xp = users[0].xp_points if users else 0

    for idx, usr in enumerate(users, start=1):
        c_bucket = campus_scores.get(usr.campus_id)
        user_entries = int(entry_counts.get(usr.id, 0))
        if c_bucket is not None:
            c_bucket["total_xp"] += int(usr.xp_points or 0)
            c_bucket["students_count"] += 1
            c_bucket["challenges_entries"] += user_entries

        is_me = bool(uid and usr.id == uid)
        if is_me:
            my_rank = idx
        individuals.append(
            {
                "rank": idx,
                "is_podium": idx <= 3,
                "user_id": usr.id,
                "username": usr.username,
                "avatar_url": usr.avatar_url,
                "campus_id": usr.campus_id,
                "campus_name": usr.campus.name if usr.campus else "",
                "xp_points": usr.xp_points,
                "challenges_joined": user_entries,
                "gap_to_leader": max(0, top_xp - usr.xp_points),
                "is_me": is_me,
            }
        )

    sorted_campuses = sorted(
        campus_scores.values(),
        key=lambda item: (-item["total_xp"], -item["challenges_entries"], item["campus_name"]),
    )
    leader_xp = sorted_campuses[0]["total_xp"] if sorted_campuses else 0
    my_campus_rank = None
    for idx, row in enumerate(sorted_campuses, start=1):
        row["rank"] = idx
        row["is_podium"] = idx <= 3
        row["gap_to_leader"] = max(0, leader_xp - row["total_xp"])
        row["is_my_campus"] = bool(my_user and my_user.campus_id == row["campus_id"])
        if row["is_my_campus"]:
            my_campus_rank = idx

    return (
        jsonify(
            {
                "campus_leaderboard": sorted_campuses,
                "individual_leaderboard": individuals,
                "my_rank": my_rank,
                "my_campus_rank": my_campus_rank,
            }
        ),
        200,
    )


@challenges_bp.get("/<int:challenge_id>/leaderboard")
@jwt_required(optional=True)
def challenge_leaderboard(challenge_id: int):
    """Retourne les podiums et classements complets d'un defi precis (US-4.3)."""
    challenge = db.session.get(Challenge, challenge_id)
    if challenge is None:
        return jsonify({"error": "Defi introuvable."}), 404
    uid = _optional_uid()
    return jsonify(_build_challenge_leaderboards(challenge, current_user_id=uid)), 200


@challenges_bp.post("")
@jwt_required()
def create_challenge():
    """Cree un nouveau defi inter-campus et inscrit son createur (US-4.1)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    sport = (data.get("sport") or "").strip()
    unit = (data.get("unit") or "").strip()
    group_id = data.get("group_id")

    try:
        target_value = float(data.get("target_value", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Objectif chiffre invalide."}), 400

    if len(title) < 3 or len(title) > 140:
        return jsonify({"error": "Le titre doit contenir entre 3 et 140 caracteres."}), 400
    if len(sport) < 2 or len(sport) > 60:
        return jsonify({"error": "La discipline sportive est requise."}), 400
    if not math.isfinite(target_value) or target_value <= 0 or target_value > 1_000_000:
        return jsonify({"error": "L'objectif doit etre strictement positif et realiste."}), 400
    if len(unit) < 1 or len(unit) > 30:
        return jsonify({"error": "L'unite de mesure est requise (ex: km, reps, min)."}), 400

    now_utc = datetime.now(timezone.utc)
    starts_at = now_utc
    if data.get("ends_at"):
        try:
            parsed_end = datetime.fromisoformat(str(data["ends_at"]).replace("Z", "+00:00"))
            ends_at = _as_utc(parsed_end)
        except ValueError:
            return jsonify({"error": "Date de fin ISO invalide."}), 400
    else:
        try:
            duration_days = int(data.get("duration_days", 7))
        except (TypeError, ValueError):
            return jsonify({"error": "Duree en jours invalide."}), 400
        if duration_days < 1 or duration_days > 365:
            return jsonify({"error": "La duree doit etre comprise entre 1 et 365 jours."}), 400
        ends_at = now_utc + timedelta(days=duration_days)

    if ends_at is None or ends_at <= starts_at:
        return jsonify({"error": "La date de fin doit etre posterieure au debut."}), 400

    if group_id is not None:
        if not isinstance(group_id, int) or db.session.get(SportGroup, group_id) is None:
            return jsonify({"error": "Groupe associe introuvable."}), 404

    challenge = Challenge(
        title=title,
        description=description[:600],
        sport=sport,
        target_value=round(target_value, 2),
        unit=unit,
        starts_at=starts_at,
        ends_at=ends_at,
        created_by=user.id,
        group_id=group_id,
    )
    db.session.add(challenge)
    db.session.flush()

    entry = ChallengeEntry(
        challenge_id=challenge.id,
        user_id=user.id,
        campus_id=user.campus_id,
        score=0.0,
    )
    user.xp_points = (user.xp_points or 0) + 15
    db.session.add(entry)
    db.session.commit()

    return (
        jsonify({"challenge": serialize_challenge(challenge, current_user_id=user.id)}),
        201,
    )


@challenges_bp.post("/<int:challenge_id>/join")
@jwt_required()
def join_challenge(challenge_id: int):
    """Inscrit un etudiant au defi en le rattachant a son campus sans doublon (US-4.1)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    challenge = db.session.get(Challenge, challenge_id)
    if challenge is None:
        return jsonify({"error": "Defi introuvable."}), 404
    if not _is_challenge_active(challenge):
        return jsonify({"error": "Ce defi est deja termine."}), 400

    existing = ChallengeEntry.query.filter_by(
        challenge_id=challenge.id,
        user_id=user.id,
    ).first()
    if existing is not None:
        return jsonify({"error": "Vous etes deja inscrit a ce defi."}), 409

    entry = ChallengeEntry(
        challenge_id=challenge.id,
        user_id=user.id,
        campus_id=user.campus_id,
        score=0.0,
    )
    user.xp_points = (user.xp_points or 0) + 10
    db.session.add(entry)
    db.session.commit()

    return (
        jsonify({"challenge": serialize_challenge(challenge, current_user_id=user.id)}),
        201,
    )


@challenges_bp.post("/<int:challenge_id>/performances")
@jwt_required()
def submit_performance(challenge_id: int):
    """Enregistre une performance validee et met a jour les scores de facon transactionnelle (US-4.2)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    challenge = db.session.get(Challenge, challenge_id)
    if challenge is None:
        return jsonify({"error": "Defi introuvable."}), 404
    if not _is_challenge_active(challenge):
        return jsonify({"error": "Impossible de soumettre sur un defi termine."}), 400

    is_multipart = bool(
        request.content_type and "multipart/form-data" in request.content_type.lower()
    )
    raw_value = (
        request.form.get("value")
        if is_multipart
        else (request.get_json(silent=True) or {}).get("value")
    )

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return jsonify({"error": "Valeur de performance numerique requise."}), 400

    max_single_submission = max(float(challenge.target_value) * 2.0, 5000.0)
    if not math.isfinite(value) or value <= 0:
        return jsonify({"error": "La performance doit etre strictement superieure a 0."}), 400
    if value > max_single_submission:
        return (
            jsonify(
                {
                    "error": f"Valeur irrealiste (plafond autorise par saisie : {max_single_submission:g} {challenge.unit})."
                }
            ),
            400,
        )

    entry = (
        ChallengeEntry.query.filter_by(
            challenge_id=challenge.id,
            user_id=user.id,
        )
        .with_for_update()
        .first()
    )
    if entry is None:
        return jsonify({"error": "Inscrivez-vous d'abord a ce defi avant de soumettre un score."}), 403

    new_proof_url = ""
    if is_multipart and request.files.get("proof_image"):
        try:
            new_proof_url = save_validated_image(
                file_storage=request.files.get("proof_image"),
                base_upload_folder=current_app.config["UPLOAD_FOLDER"],
                subfolder="proofs",
                max_size=(1080, 1080),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    old_proof = entry.proof_media_url if new_proof_url else ""
    entry.score = round(float(entry.score or 0.0) + value, 2)
    entry.updated_at = datetime.now(timezone.utc)
    if new_proof_url:
        entry.proof_media_url = new_proof_url

    # Trace l'effort dans le journal d'entrainement et credite de l'XP
    unit_lower = challenge.unit.lower()
    duration_est = int(value) if "min" in unit_lower else 30
    dist_est = round(value, 2) if "km" in unit_lower else 0.0
    db.session.add(
        Workout(
            user_id=user.id,
            sport=challenge.sport,
            duration_minutes=max(1, min(duration_est, 600)),
            calories=int(max(40, min(value * 35, 2500))),
            distance_km=dist_est,
            source="challenge",
        )
    )
    user.xp_points = (user.xp_points or 0) + 20
    db.session.commit()
    evaluate_and_award_badges(user.id)

    if old_proof:
        remove_uploaded_file(old_proof, current_app.config["UPLOAD_FOLDER"])

    return jsonify(_build_challenge_leaderboards(challenge, current_user_id=user.id)), 200


@challenges_bp.delete("/<int:challenge_id>")
@jwt_required()
def delete_challenge(challenge_id: int):
    """Supprime un defi (reserve a son createur)."""
    uid = int(get_jwt_identity())
    challenge = db.session.get(Challenge, challenge_id)
    if challenge is None:
        return jsonify({"error": "Defi introuvable."}), 404
    if challenge.created_by != uid:
        return jsonify({"error": "Seul le createur peut supprimer ce defi."}), 403

    entries = ChallengeEntry.query.filter_by(challenge_id=challenge.id).all()
    proof_urls = [e.proof_media_url for e in entries if e.proof_media_url]

    db.session.delete(challenge)
    db.session.commit()

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    for url in proof_urls:
        remove_uploaded_file(url, upload_folder)

    return jsonify({"deleted": True, "challenge_id": challenge_id}), 200
