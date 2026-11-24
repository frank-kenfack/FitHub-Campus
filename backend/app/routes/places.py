"""Routes Geolocalisation : Salles, Spots & Evenements Locaux (Etape 6 : US-6.1, US-6.2, US-6.3)."""

import math
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Campus, EventRsvp, PlaceEvent, User
from app.utils.gamification import evaluate_and_award_badges, haversine_km

places_bp = Blueprint("places", __name__, url_prefix="/api/places")


def _optional_uid() -> int | None:
    raw = get_jwt_identity()
    return int(raw) if raw is not None else None


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def serialize_place(
    place: PlaceEvent,
    current_user_id: int | None = None,
    distance_km: float | None = None,
) -> dict:
    """Serialise un lieu sportif ou evenement geolocalise avec capacite RSVP."""
    campus = db.session.get(Campus, place.campus_id)
    creator = db.session.get(User, place.created_by) if place.created_by else None

    rsvps = (
        EventRsvp.query.filter_by(event_id=place.id)
        .order_by(EventRsvp.created_at.asc(), EventRsvp.id.asc())
        .all()
    )
    rsvp_count = len(rsvps)
    rsvp_uids = {r.user_id for r in rsvps}

    max_cap = place.max_participants
    is_full = bool(max_cap is not None and rsvp_count >= max_cap)
    spots_left = max(0, max_cap - rsvp_count) if max_cap is not None else None

    participants = []
    for r in rsvps[:12]:
        u = db.session.get(User, r.user_id)
        if u is not None:
            participants.append(
                {
                    "user_id": u.id,
                    "username": u.username,
                    "avatar_url": u.avatar_url,
                }
            )

    return {
        "id": place.id,
        "campus_id": place.campus_id,
        "campus_name": campus.name if campus else "",
        "campus_city": campus.city if campus else "",
        "created_by": place.created_by,
        "creator_username": creator.username if creator else "FitHub Campus",
        "title": place.title,
        "kind": place.kind,
        "sport": place.sport,
        "description": place.description,
        "address": place.address,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "starts_at": place.starts_at.isoformat() if place.starts_at else None,
        "max_participants": max_cap,
        "rsvp_count": rsvp_count,
        "spots_left": spots_left,
        "is_full": is_full,
        "is_going": bool(current_user_id and current_user_id in rsvp_uids),
        "participants": participants,
        "created_at": place.created_at.isoformat() if place.created_at else None,
    }


@places_bp.get("")
@jwt_required(optional=True)
def list_places():
    """Liste les salles, spots et evenements avec filtrage Haversine par rayon (US-6.1, US-6.3)."""
    uid = _optional_uid()
    campus_id = request.args.get("campus_id", type=int)
    kind = (request.args.get("kind") or "all").strip().lower()
    sport = (request.args.get("sport") or "").strip()

    raw_lat = request.args.get("lat")
    raw_lon = request.args.get("lon")
    raw_radius = request.args.get("radius_km")

    ref_lat: float | None = None
    ref_lon: float | None = None
    ref_source: str | None = None

    if (raw_lat is not None and raw_lat != "") or (raw_lon is not None and raw_lon != ""):
        if not raw_lat or not raw_lon:
            return jsonify({"error": "Les parametres lat et lon doivent etre fournis ensemble."}), 400
        try:
            ref_lat = float(raw_lat)
            ref_lon = float(raw_lon)
        except ValueError:
            return jsonify({"error": "Coordonnees GPS lat/lon invalides."}), 400
        if not (
            math.isfinite(ref_lat)
            and math.isfinite(ref_lon)
            and -90.0 <= ref_lat <= 90.0
            and -180.0 <= ref_lon <= 180.0
        ):
            return jsonify({"error": "Coordonnees GPS hors limites (-90..90, -180..180)."}), 400
        ref_source = "gps"
    elif campus_id is not None:
        campus_ref = db.session.get(Campus, campus_id)
        if campus_ref is not None:
            ref_lat = campus_ref.latitude
            ref_lon = campus_ref.longitude
            ref_source = "campus"
    elif uid is not None:
        usr = db.session.get(User, uid)
        if usr and usr.campus:
            ref_lat = usr.campus.latitude
            ref_lon = usr.campus.longitude
            ref_source = "user_campus"

    radius_km: float | None = None
    if raw_radius is not None and raw_radius != "":
        try:
            radius_km = float(raw_radius)
        except ValueError:
            return jsonify({"error": "Rayon en km invalide."}), 400
        if not math.isfinite(radius_km) or radius_km <= 0 or radius_km > 2000:
            return jsonify({"error": "Le rayon doit etre compris entre 0.1 et 2000 km."}), 400
        if ref_lat is None or ref_lon is None:
            return (
                jsonify(
                    {
                        "error": "Fournissez lat/lon ou campus_id pour filtrer par rayon kilometrique."
                    }
                ),
                400,
            )

    query = PlaceEvent.query
    if kind in {"gym", "spot", "event"}:
        query = query.filter(PlaceEvent.kind == kind)
    if sport:
        pattern = f"%{sport}%"
        query = query.filter(
            db.or_(
                PlaceEvent.sport.ilike(pattern),
                PlaceEvent.title.ilike(pattern),
            )
        )
    if campus_id is not None and radius_km is None:
        query = query.filter(PlaceEvent.campus_id == campus_id)

    rows = query.order_by(PlaceEvent.created_at.desc(), PlaceEvent.id.asc()).all()

    enriched: list[tuple[float | None, PlaceEvent]] = []
    for place in rows:
        dist: float | None = None
        if ref_lat is not None and ref_lon is not None:
            dist = haversine_km(ref_lat, ref_lon, place.latitude, place.longitude)
            if radius_km is not None and dist > radius_km:
                continue
        enriched.append((dist, place))

    if ref_lat is not None and ref_lon is not None:
        enriched.sort(key=lambda pair: (pair[0] if pair[0] is not None else 999999.0, pair[1].id))

    return (
        jsonify(
            {
                "places": [
                    serialize_place(p, current_user_id=uid, distance_km=d)
                    for d, p in enriched
                ],
                "reference_point": (
                    {
                        "latitude": ref_lat,
                        "longitude": ref_lon,
                        "source": ref_source,
                        "radius_km": radius_km,
                    }
                    if ref_lat is not None and ref_lon is not None
                    else None
                ),
            }
        ),
        200,
    )


@places_bp.post("/events")
@jwt_required()
def create_geolocated_event():
    """Cree un evenement sportif geolocalise et inscrit automatiquement l'organisateur (US-6.2)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    sport = (data.get("sport") or "").strip()
    description = (data.get("description") or "").strip()
    address = (data.get("address") or "").strip()
    campus_id = data.get("campus_id") or user.campus_id

    try:
        campus_id_int = int(campus_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Identifiant de campus invalide."}), 400

    campus = db.session.get(Campus, campus_id_int)
    if campus is None:
        return jsonify({"error": "Campus introuvable."}), 404

    if len(title) < 3 or len(title) > 140:
        return jsonify({"error": "Le titre doit contenir entre 3 et 140 caracteres."}), 400
    if len(sport) < 2 or len(sport) > 60:
        return jsonify({"error": "La discipline sportive est requise."}), 400

    raw_lat = data.get("latitude", campus.latitude)
    raw_lon = data.get("longitude", campus.longitude)
    try:
        latitude = float(raw_lat)
        longitude = float(raw_lon)
    except (TypeError, ValueError):
        return jsonify({"error": "Coordonnees GPS latitude/longitude invalides."}), 400

    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    ):
        return jsonify({"error": "Coordonnees GPS hors limites geographiques."}), 400

    raw_max = data.get("max_participants", 15)
    try:
        max_participants = int(raw_max)
    except (TypeError, ValueError):
        return jsonify({"error": "Nombre maximal de participants invalide."}), 400
    if max_participants < 1 or max_participants > 500:
        return (
            jsonify({"error": "La capacite doit etre comprise entre 1 et 500 participants."}),
            400,
        )

    raw_starts = data.get("starts_at")
    if not raw_starts:
        return jsonify({"error": "La date et l'heure de l'evenement (starts_at) sont requises."}), 400
    try:
        starts_at = _as_utc(datetime.fromisoformat(str(raw_starts).replace("Z", "+00:00")))
    except ValueError:
        return jsonify({"error": "Format de date ISO invalide pour starts_at."}), 400

    event_place = PlaceEvent(
        campus_id=campus.id,
        created_by=user.id,
        title=title,
        kind="event",
        sport=sport,
        description=description[:600],
        address=address[:200] or f"Autour de {campus.name}",
        latitude=round(latitude, 6),
        longitude=round(longitude, 6),
        starts_at=starts_at,
        max_participants=max_participants,
    )
    db.session.add(event_place)
    db.session.flush()

    db.session.add(EventRsvp(event_id=event_place.id, user_id=user.id))
    user.xp_points = (user.xp_points or 0) + 20
    db.session.commit()

    unlocked = evaluate_and_award_badges(user.id)
    return (
        jsonify(
            {
                "place": serialize_place(event_place, current_user_id=user.id),
                "newly_unlocked_badges": unlocked,
            }
        ),
        201,
    )


@places_bp.post("/<int:place_id>/rsvp")
@jwt_required()
def rsvp_place_event(place_id: int):
    """Confirme ou annule la participation a un evenement dans le respect de sa capacite (US-6.2)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    place = (
        PlaceEvent.query.filter_by(id=place_id)
        .with_for_update()
        .first()
    )
    if place is None:
        return jsonify({"error": "Lieu ou evenement introuvable."}), 404

    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "toggle").strip().lower()
    if action not in {"join", "leave", "toggle"}:
        return jsonify({"error": "Action RSVP invalide (join, leave ou toggle)."}), 400

    existing = EventRsvp.query.filter_by(event_id=place.id, user_id=user.id).first()
    current_count = EventRsvp.query.filter_by(event_id=place.id).count()
    unlocked: list[dict] = []

    want_join = action == "join" or (action == "toggle" and existing is None)

    if want_join:
        if existing is None:
            if place.max_participants is not None and current_count >= place.max_participants:
                return (
                    jsonify(
                        {
                            "error": "Cet evenement est complet (capacite maximale atteinte)."
                        }
                    ),
                    409,
                )
            db.session.add(EventRsvp(event_id=place.id, user_id=user.id))
            user.xp_points = (user.xp_points or 0) + 10
            db.session.commit()
            unlocked = evaluate_and_award_badges(user.id)
        is_going = True
    else:
        if existing is not None:
            db.session.delete(existing)
            user.xp_points = max(0, int(user.xp_points or 0) - 10)
            db.session.commit()
        is_going = False

    serialized = serialize_place(place, current_user_id=user.id)
    return (
        jsonify(
            {
                "place": serialized,
                "is_going": is_going,
                "rsvp_count": serialized["rsvp_count"],
                "newly_unlocked_badges": unlocked,
            }
        ),
        200,
    )


@places_bp.delete("/<int:place_id>")
@jwt_required()
def delete_place_event(place_id: int):
    """Supprime un evenement geolocalise (reserve exclusivement a son createur)."""
    uid = int(get_jwt_identity())
    place = db.session.get(PlaceEvent, place_id)
    if place is None:
        return jsonify({"error": "Lieu ou evenement introuvable."}), 404
    if not place.created_by or place.created_by != uid:
        return jsonify({"error": "Seul l'organisateur peut supprimer cet evenement."}), 403

    db.session.delete(place)
    db.session.commit()
    return jsonify({"deleted": True, "place_id": place_id}), 200
