"""Moteur de gamification FitHub Campus (badges, paliers et import d'activites)."""

import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from app.extensions import db
from app.models import (
    Badge,
    Challenge,
    ChallengeEntry,
    Encouragement,
    EventRsvp,
    Story,
    User,
    UserBadge,
    Workout,
)

EARTH_RADIUS_KM = 6371.0088

REWARD_TIERS = [
    {
        "level": 1,
        "code": "bronze",
        "name": "Athlete Bronze",
        "min_xp": 0,
        "max_xp": 199,
        "reward": "Badge Profil Etudiant Actif et Cadre Campus Bronze",
    },
    {
        "level": 2,
        "code": "silver",
        "name": "Athlete Argent",
        "min_xp": 200,
        "max_xp": 399,
        "reward": "Pass Prioritaire Evenements BDE et Bandeau Argent",
    },
    {
        "level": 3,
        "code": "gold",
        "name": "Athlete Or",
        "min_xp": 400,
        "max_xp": 649,
        "reward": "Acces Seances Coaching Partenaires et Titre Ambassadeur",
    },
    {
        "level": 4,
        "code": "legend",
        "name": "Legende Campus",
        "min_xp": 650,
        "max_xp": None,
        "reward": "Trophee Tableau d'Honneur Inter-Campus et Kit Officiel FitHub",
    },
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c


def _is_user_on_challenge_campus_podium(user_id: int) -> bool:
    user_entries = ChallengeEntry.query.filter(
        ChallengeEntry.user_id == user_id,
        ChallengeEntry.score > 0,
    ).all()
    if not user_entries:
        return False

    for ue in user_entries:
        all_entries = ChallengeEntry.query.filter_by(challenge_id=ue.challenge_id).all()
        campus_totals: dict[int, float] = {}
        for item in all_entries:
            campus_totals[item.campus_id] = campus_totals.get(item.campus_id, 0.0) + float(
                item.score or 0.0
            )
        ranked_campus_ids = [
            cid
            for cid, score in sorted(
                campus_totals.items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
            if score > 0
        ]
        if ue.campus_id in ranked_campus_ids[:3]:
            return True
    return False


def evaluate_and_award_badges(user_id: int) -> list[dict]:
    user = db.session.get(User, user_id)
    if user is None:
        return []

    badges_by_code = {b.code: b for b in Badge.query.all()}
    if not badges_by_code:
        return []

    existing_badge_ids = {
        ub.badge_id for ub in UserBadge.query.filter_by(user_id=user.id).all()
    }

    workouts_count = Workout.query.filter_by(user_id=user.id).count()
    stories_count = Story.query.filter_by(user_id=user.id).count()
    encouragements_sent = Encouragement.query.filter_by(sender_id=user.id).count()
    events_rsvp_count = EventRsvp.query.filter_by(user_id=user.id).count()

    criteria_met = {
        "first_workout": workouts_count >= 1 or stories_count >= 1,
        "five_workouts": workouts_count >= 5,
        "fit_buddy_solidarity": encouragements_sent >= 1,
        "top_campus": _is_user_on_challenge_campus_podium(user.id),
        "event_participant": events_rsvp_count >= 1,
    }

    newly_unlocked: list[dict] = []
    for code, is_met in criteria_met.items():
        badge = badges_by_code.get(code)
        if badge is None or not is_met or badge.id in existing_badge_ids:
            continue
        ub = UserBadge(user_id=user.id, badge_id=badge.id)
        db.session.add(ub)
        existing_badge_ids.add(badge.id)
        newly_unlocked.append(
            {
                "id": badge.id,
                "code": badge.code,
                "name": badge.name,
                "description": badge.description,
                "xp_reward": badge.xp_reward,
            }
        )

    if newly_unlocked:
        db.session.commit()

    return newly_unlocked


def compute_reward_progression(total_xp: int) -> dict:
    xp = max(0, int(total_xp or 0))
    current_idx = 0
    for idx, tier in enumerate(REWARD_TIERS):
        if xp >= tier["min_xp"]:
            current_idx = idx

    current_tier = REWARD_TIERS[current_idx]
    next_tier = REWARD_TIERS[current_idx + 1] if current_idx + 1 < len(REWARD_TIERS) else None

    if next_tier is not None:
        span = max(1, next_tier["min_xp"] - current_tier["min_xp"])
        gained_in_tier = xp - current_tier["min_xp"]
        progress_pct = round(min(100.0, max(0.0, (gained_in_tier / span) * 100.0)), 1)
        xp_to_next = max(0, next_tier["min_xp"] - xp)
    else:
        progress_pct = 100.0
        xp_to_next = 0

    tiers_catalog = [
        {
            **t,
            "unlocked": xp >= t["min_xp"],
            "is_current": t["level"] == current_tier["level"],
        }
        for t in REWARD_TIERS
    ]

    return {
        "current_tier": current_tier,
        "next_tier": next_tier,
        "progress_pct": progress_pct,
        "xp_to_next": xp_to_next,
        "tiers": tiers_catalog,
    }


def build_gamification_summary(user: User) -> dict:
    newly_unlocked = evaluate_and_award_badges(user.id)

    all_badges = Badge.query.order_by(Badge.id.asc()).all()
    user_badges_map = {
        ub.badge_id: ub
        for ub in UserBadge.query.filter_by(user_id=user.id).all()
    }

    badges_payload = []
    badges_xp = 0
    for b in all_badges:
        ub = user_badges_map.get(b.id)
        is_unlocked = ub is not None
        if is_unlocked:
            badges_xp += int(b.xp_reward or 0)
        badges_payload.append(
            {
                "id": b.id,
                "code": b.code,
                "name": b.name,
                "description": b.description,
                "xp_reward": b.xp_reward,
                "unlocked": is_unlocked,
                "awarded_at": ub.awarded_at.isoformat() if ub and ub.awarded_at else None,
            }
        )

    activity_xp = int(user.xp_points or 0)
    total_xp = activity_xp + badges_xp
    progression = compute_reward_progression(total_xp)

    recent_workouts = (
        Workout.query.filter_by(user_id=user.id)
        .order_by(Workout.performed_at.desc(), Workout.id.desc())
        .limit(8)
        .all()
    )

    return {
        "user_id": user.id,
        "username": user.username,
        "activity_xp": activity_xp,
        "badges_xp": badges_xp,
        "total_xp": total_xp,
        "unlocked_count": len(user_badges_map),
        "total_badges": len(all_badges),
        "badges": badges_payload,
        "newly_unlocked_badges": newly_unlocked,
        "progression": progression,
        "recent_workouts": [
            {
                "id": w.id,
                "sport": w.sport,
                "duration_minutes": w.duration_minutes,
                "calories": w.calories,
                "distance_km": round(float(w.distance_km or 0.0), 2),
                "source": w.source,
                "performed_at": w.performed_at.isoformat() if w.performed_at else None,
            }
            for w in recent_workouts
        ],
    }


GOOGLE_FIT_ACTIVITY_MAP = {
    7: "Marche",
    8: "Running",
    1: "Cyclisme",
    9: "Aerobic",
    82: "Natation",
    97: "Musculation",
    113: "Cross-Training",
}


def parse_gpx_bytes(raw_bytes: bytes, fallback_sport: str = "Running") -> dict:
    # Empeche toute attaque XXE avant l'analyse XML standard.
    text_preview = raw_bytes[:2048].decode("utf-8", errors="ignore").upper()
    if "<!DOCTYPE" in text_preview or "<!ENTITY" in text_preview:
        raise ValueError("Fichier GPX invalide (entites XML externes interdites).")

    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as exc:
        raise ValueError("Fichier XML GPX malforme.") from exc

    sport_name = fallback_sport
    points: list[tuple[float, float]] = []
    timestamps: list[datetime] = []

    for elem in root.iter():
        local_tag = elem.tag.split("}")[-1].lower()
        if local_tag == "type" and elem.text and elem.text.strip():
            sport_name = elem.text.strip()[:60]
        elif local_tag == "trkpt":
            try:
                lat = float(elem.attrib["lat"])
                lon = float(elem.attrib["lon"])
            except (KeyError, ValueError) as exc:
                raise ValueError("Coordonnees GPS manquantes ou invalides dans <trkpt>.") from exc
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                raise ValueError("Coordonnees GPX hors limites geographiques.")
            points.append((lat, lon))
            for child in elem:
                if child.tag.split("}")[-1].lower() == "time" and child.text:
                    try:
                        ts = datetime.fromisoformat(child.text.strip().replace("Z", "+00:00"))
                        timestamps.append(ts)
                    except ValueError:
                        pass

    if len(points) < 2:
        raise ValueError("Le fichier GPX doit contenir au moins 2 points GPS (<trkpt>).")

    total_km = 0.0
    for idx in range(1, len(points)):
        lat1, lon1 = points[idx - 1]
        lat2, lon2 = points[idx]
        total_km += haversine_km(lat1, lon1, lat2, lon2)

    distance_km = round(max(0.05, total_km), 2)
    if len(timestamps) >= 2 and timestamps[-1] > timestamps[0]:
        delta_min = int(round((timestamps[-1] - timestamps[0]).total_seconds() / 60.0))
        duration_minutes = max(1, min(1440, delta_min))
    else:
        duration_minutes = max(5, min(1440, int(round(distance_km * 6.0))))

    calories = max(30, int(round(distance_km * 62.0)))
    return {
        "sport": sport_name,
        "duration_minutes": duration_minutes,
        "distance_km": distance_km,
        "calories": calories,
        "source": "gpx",
        "points_count": len(points),
    }


def normalize_json_activities(payload: dict | list, default_source: str = "google_fit") -> list[dict]:
    raw_items: list[dict]
    source = default_source

    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        source = str(payload.get("source") or default_source).strip()[:40] or "google_fit"
        if isinstance(payload.get("sessions"), list):
            raw_items = payload["sessions"]
            source = "google_fit"
        elif isinstance(payload.get("activities"), list):
            raw_items = payload["activities"]
        else:
            raw_items = [payload]
    else:
        raise ValueError("Format JSON d'activite non reconnu.")

    if not raw_items:
        raise ValueError("Aucune activite sportive trouvee dans les donnees importees.")
    if len(raw_items) > 25:
        raise ValueError("Import limite a 25 seances simultanement.")

    normalized: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Chaque activite importee doit etre un objet JSON.")

        act_type = item.get("activityType")
        sport = str(
            item.get("sport")
            or GOOGLE_FIT_ACTIVITY_MAP.get(act_type, "")
            or item.get("name")
            or "Running"
        ).strip()[:60]

        if "duration_minutes" in item and item["duration_minutes"] is not None:
            duration_minutes = int(float(item["duration_minutes"]))
        elif "startTimeMillis" in item and "endTimeMillis" in item:
            ms = int(item["endTimeMillis"]) - int(item["startTimeMillis"])
            duration_minutes = max(1, int(round(ms / 60000.0)))
        else:
            raise ValueError("Duree manquante (duration_minutes ou startTimeMillis/endTimeMillis).")

        if "distance_km" in item and item["distance_km"] is not None:
            distance_km = float(item["distance_km"])
        elif "distanceMeters" in item and item["distanceMeters"] is not None:
            distance_km = float(item["distanceMeters"]) / 1000.0
        else:
            distance_km = 0.0

        calories = int(float(item.get("calories") or max(40, duration_minutes * 8)))

        if duration_minutes <= 0 or duration_minutes > 1440:
            raise ValueError("La duree d'une seance doit etre comprise entre 1 et 1440 minutes.")
        if not math.isfinite(distance_km) or distance_km < 0 or distance_km > 500:
            raise ValueError("Distance en km invalide (0 a 500 km).")
        if calories < 0 or calories > 15000:
            raise ValueError("Nombre de calories invalide.")

        normalized.append(
            {
                "sport": sport if len(sport) >= 2 else "Fitness",
                "duration_minutes": duration_minutes,
                "distance_km": round(distance_km, 2),
                "calories": calories,
                "source": str(item.get("source") or source)[:40],
            }
        )

    return normalized


def parse_uploaded_activity_file(filename: str, raw_bytes: bytes, fallback_sport: str = "Running") -> list[dict]:
    if not raw_bytes:
        raise ValueError("Le fichier d'activite est vide.")
    if len(raw_bytes) > 2 * 1024 * 1024:
        raise ValueError("Fichier trop volumineux (max 2 Mo).")

    lower_name = (filename or "").lower()
    if lower_name.endswith(".gpx"):
        return [parse_gpx_bytes(raw_bytes, fallback_sport=fallback_sport)]
    if lower_name.endswith(".json"):
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Fichier JSON malforme.") from exc
        return normalize_json_activities(parsed, default_source="json_import")

    raise ValueError("Format non supporte : veuillez importer un fichier .gpx ou .json.")


def credit_challenge_from_workout(
    user: User,
    workout_entry: dict,
    explicit_challenge_id: int | None = None,
) -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    updates: list[dict] = []

    target_challenges: list[Challenge] = []
    if explicit_challenge_id is not None:
        ch = db.session.get(Challenge, explicit_challenge_id)
        if ch is None:
            raise ValueError("Defi cible introuvable.")
        ends_utc = ch.ends_at if ch.ends_at.tzinfo else ch.ends_at.replace(tzinfo=timezone.utc)
        if ends_utc < now_utc:
            raise ValueError("Le defi cible est deja termine.")
        target_challenges.append(ch)
    else:
        joined_entries = ChallengeEntry.query.filter_by(user_id=user.id).all()
        for entry in joined_entries:
            ch = db.session.get(Challenge, entry.challenge_id)
            if ch is None:
                continue
            ends_utc = ch.ends_at if ch.ends_at.tzinfo else ch.ends_at.replace(tzinfo=timezone.utc)
            if ends_utc >= now_utc and ch.sport.lower() in workout_entry["sport"].lower():
                target_challenges.append(ch)

    for ch in target_challenges:
        unit_lower = ch.unit.lower()
        if "km" in unit_lower:
            delta = float(workout_entry["distance_km"])
        elif "min" in unit_lower:
            delta = float(workout_entry["duration_minutes"])
        elif "cal" in unit_lower or "kcal" in unit_lower:
            delta = float(workout_entry["calories"])
        else:
            delta = float(workout_entry["duration_minutes"])

        if delta <= 0:
            continue

        # Verrou pessimiste sur la ligne de participation pour eviter toute perte de score concurrente.
        entry = (
            ChallengeEntry.query.filter_by(challenge_id=ch.id, user_id=user.id)
            .with_for_update()
            .first()
        )
        if entry is None:
            entry = ChallengeEntry(
                challenge_id=ch.id,
                user_id=user.id,
                campus_id=user.campus_id,
                score=0.0,
            )
            db.session.add(entry)
            db.session.flush()

        entry.score = round(float(entry.score or 0.0) + delta, 2)
        entry.updated_at = now_utc
        updates.append(
            {
                "challenge_id": ch.id,
                "title": ch.title,
                "unit": ch.unit,
                "added_score": round(delta, 2),
                "new_score": entry.score,
            }
        )

    return updates
