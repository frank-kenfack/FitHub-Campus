"""Logique metier partagee (REST + Socket.IO) pour Fit-Buddy, Streak et Encouragements."""

from datetime import date, datetime, timedelta, timezone

from app.extensions import db, socketio
from app.models import Campus, Encouragement, FitBuddy, Story, User, Workout


def find_buddy_relation(user_a_id: int, user_b_id: int) -> FitBuddy | None:
    """Recherche une relation FitBuddy existante entre deux etudiants (dans les 2 sens)."""
    return FitBuddy.query.filter(
        db.or_(
            db.and_(
                FitBuddy.requester_id == user_a_id,
                FitBuddy.addressee_id == user_b_id,
            ),
            db.and_(
                FitBuddy.requester_id == user_b_id,
                FitBuddy.addressee_id == user_a_id,
            ),
        )
    ).first()


def compute_pair_streak_days(relation: FitBuddy) -> int:
    """Calcule le nombre de jours consecutifs d'activite du binome (US-5.3)."""
    uids = [relation.requester_id, relation.addressee_id]
    active_dates: set[date] = set()

    for (dt,) in (
        db.session.query(Workout.performed_at)
        .filter(Workout.user_id.in_(uids))
        .all()
    ):
        if dt:
            active_dates.add(dt.astimezone(timezone.utc).date() if dt.tzinfo else dt.date())

    for (dt,) in (
        db.session.query(Story.created_at)
        .filter(Story.user_id.in_(uids))
        .all()
    ):
        if dt:
            active_dates.add(dt.astimezone(timezone.utc).date() if dt.tzinfo else dt.date())

    for (dt,) in (
        db.session.query(Encouragement.created_at)
        .filter(
            db.or_(
                db.and_(
                    Encouragement.sender_id == uids[0],
                    Encouragement.receiver_id == uids[1],
                ),
                db.and_(
                    Encouragement.sender_id == uids[1],
                    Encouragement.receiver_id == uids[0],
                ),
            )
        )
        .all()
    ):
        if dt:
            active_dates.add(dt.astimezone(timezone.utc).date() if dt.tzinfo else dt.date())

    today = datetime.now(timezone.utc).date()
    cursor = today if today in active_dates else (today - timedelta(days=1))
    consecutive = 0
    while cursor in active_dates:
        consecutive += 1
        cursor -= timedelta(days=1)

    updated_streak = max(int(relation.streak_days or 0), consecutive)
    if relation.status == "accepted" and updated_streak == 0:
        updated_streak = 1
    if updated_streak != relation.streak_days:
        relation.streak_days = updated_streak
        db.session.commit()
    return updated_streak


def serialize_encouragement(enc: Encouragement) -> dict:
    """Serialise un message d'encouragement temps reel."""
    sender = db.session.get(User, enc.sender_id)
    receiver = db.session.get(User, enc.receiver_id)
    return {
        "id": enc.id,
        "sender_id": enc.sender_id,
        "sender_username": sender.username if sender else "Etudiant",
        "sender_avatar_url": sender.avatar_url if sender else "",
        "receiver_id": enc.receiver_id,
        "receiver_username": receiver.username if receiver else "Etudiant",
        "message": enc.message,
        "created_at": enc.created_at.isoformat() if enc.created_at else None,
    }


def serialize_buddy_relation(relation: FitBuddy, current_user_id: int) -> dict:
    """Serialise une relation FitBuddy du point de vue de current_user_id."""
    partner_id = (
        relation.addressee_id
        if relation.requester_id == current_user_id
        else relation.requester_id
    )
    partner = db.session.get(User, partner_id)
    campus = db.session.get(Campus, partner.campus_id) if partner else None
    streak = compute_pair_streak_days(relation) if relation.status == "accepted" else 0

    return {
        "id": relation.id,
        "status": relation.status,
        "direction": "sent" if relation.requester_id == current_user_id else "received",
        "streak_days": streak,
        "created_at": relation.created_at.isoformat() if relation.created_at else None,
        "partner": {
            "id": partner.id if partner else partner_id,
            "username": partner.username if partner else "Etudiant",
            "avatar_url": partner.avatar_url if partner else "",
            "campus_id": partner.campus_id if partner else None,
            "campus_name": campus.name if campus else "",
            "favorite_sports": partner.favorite_sports if partner else "",
            "level": partner.level if partner else "",
            "xp_points": partner.xp_points if partner else 0,
        },
    }


def create_and_emit_encouragement(
    sender_id: int,
    receiver_id: int,
    raw_message: str,
) -> tuple[dict | None, str | None, int]:
    """Persiste un encouragement entre buddies actifs et le diffuse via Socket.IO."""
    message = (raw_message or "").strip()
    if not message or len(message) > 280:
        return None, "Le message doit contenir entre 1 et 280 caracteres.", 400

    if sender_id == receiver_id:
        return None, "Impossible de s'envoyer un encouragement a soi-meme.", 400

    receiver = db.session.get(User, receiver_id)
    sender = db.session.get(User, sender_id)
    if sender is None or receiver is None:
        return None, "Utilisateur introuvable.", 404

    relation = find_buddy_relation(sender_id, receiver_id)
    if relation is None or relation.status != "accepted":
        return None, "Vous devez etre Fit-Buddies acceptes pour echanger en direct.", 403

    enc = Encouragement(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message=message,
    )
    sender.xp_points = (sender.xp_points or 0) + 5
    db.session.add(enc)
    db.session.commit()

    streak = compute_pair_streak_days(relation)
    payload = serialize_encouragement(enc)
    payload["streak_days"] = streak

    socketio.emit("new_encouragement", payload, to=f"user_{receiver_id}")
    socketio.emit("new_encouragement", payload, to=f"user_{sender_id}")
    return payload, None, 201
