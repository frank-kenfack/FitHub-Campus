"""Routes Gamification, Badges & Import d'activites externes (Etape 6 : US-7.1, US-7.2, US-7.3)."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import User, Workout
from app.services.badge_progression import (
    build_gamification_summary,
    credit_challenge_from_workout,
    evaluate_and_award_badges,
    normalize_json_activities,
    parse_uploaded_activity_file,
)

gamification_bp = Blueprint("gamification", __name__, url_prefix="/api/gamification")


@gamification_bp.get("/summary")
@jwt_required()
def get_gamification_summary():
    """Retourne les 5 badges (debloques/verrouilles), le palier XP et les seances recentes."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    return jsonify(build_gamification_summary(user)), 200


@gamification_bp.post("/import-activity")
@jwt_required()
def import_external_activity():
    """Importe une ou plusieurs seances (Google Fit JSON ou fichier .gpx/.json) (US-7.3)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    is_multipart = bool(
        request.content_type and "multipart/form-data" in request.content_type.lower()
    )

    explicit_challenge_id: int | None = None
    try:
        if is_multipart:
            uploaded = request.files.get("file")
            if uploaded is None or not uploaded.filename:
                return jsonify({"error": "Veuillez joindre un fichier .gpx ou .json."}), 400
            fallback_sport = (request.form.get("sport") or "Running").strip()
            raw_cid = request.form.get("challenge_id")
            if raw_cid:
                explicit_challenge_id = int(raw_cid)
            activities = parse_uploaded_activity_file(
                filename=uploaded.filename,
                raw_bytes=uploaded.read(),
                fallback_sport=fallback_sport,
            )
        else:
            payload = request.get_json(silent=True)
            if payload is None:
                return jsonify({"error": "Corps JSON ou fichier .gpx/.json requis."}), 400
            if isinstance(payload, dict) and payload.get("challenge_id") is not None:
                explicit_challenge_id = int(payload["challenge_id"])
            activities = normalize_json_activities(payload, default_source="google_fit")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    created_workouts: list[Workout] = []
    challenge_updates: list[dict] = []

    try:
        for act in activities:
            w = Workout(
                user_id=user.id,
                sport=act["sport"],
                duration_minutes=act["duration_minutes"],
                calories=act["calories"],
                distance_km=act["distance_km"],
                source=act["source"],
            )
            db.session.add(w)
            created_workouts.append(w)
            updates = credit_challenge_from_workout(
                user=user,
                workout_entry=act,
                explicit_challenge_id=explicit_challenge_id,
            )
            challenge_updates.extend(updates)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400

    xp_gained = 30 * len(created_workouts)
    user.xp_points = (user.xp_points or 0) + xp_gained
    db.session.commit()

    newly_unlocked = evaluate_and_award_badges(user.id)
    summary = build_gamification_summary(user)
    summary["newly_unlocked_badges"] = newly_unlocked

    return (
        jsonify(
            {
                "imported_count": len(created_workouts),
                "xp_gained": xp_gained,
                "imported_workouts": [
                    {
                        "id": w.id,
                        "sport": w.sport,
                        "duration_minutes": w.duration_minutes,
                        "distance_km": w.distance_km,
                        "calories": w.calories,
                        "source": w.source,
                    }
                    for w in created_workouts
                ],
                "challenge_updates": challenge_updates,
                "newly_unlocked_badges": newly_unlocked,
                "summary": summary,
            }
        ),
        201,
    )
