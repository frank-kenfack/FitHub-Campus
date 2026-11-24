"""Serialiseurs JSON pour les utilisateurs et groupes sportifs."""

from app.extensions import db
from app.models import Badge, Campus, GroupMember, SportGroup, User, UserBadge, Workout


def serialize_user(user: User, include_stats: bool = False) -> dict:
    """Convertit un objet User en dictionnaire JSON sans exposer password_hash."""
    payload = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "campus_id": user.campus_id,
        "campus_name": user.campus.name if user.campus else "",
        "campus_city": user.campus.city if user.campus else "",
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "favorite_sports": user.favorite_sports,
        "level": user.level,
        "xp_points": user.xp_points,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
    if include_stats:
        workouts_count = Workout.query.filter_by(user_id=user.id).count()
        groups_count = GroupMember.query.filter_by(user_id=user.id).count()
        awarded = (
            Badge.query.join(UserBadge, UserBadge.badge_id == Badge.id)
            .filter(UserBadge.user_id == user.id)
            .order_by(Badge.id.asc())
            .all()
        )
        payload["stats"] = {
            "workouts_count": workouts_count,
            "groups_count": groups_count,
            "badges_count": len(awarded),
            "xp_points": user.xp_points,
        }
        payload["badges"] = [
            {
                "id": b.id,
                "code": b.code,
                "name": b.name,
                "description": b.description,
                "xp_reward": b.xp_reward,
            }
            for b in awarded
        ]
    return payload


def serialize_group(
    group: SportGroup,
    current_user_id: int | None = None,
    include_members: bool = False,
) -> dict:
    """Convertit un SportGroup en dictionnaire JSON enrichi."""
    memberships = (
        GroupMember.query.filter_by(group_id=group.id)
        .order_by(GroupMember.joined_at.asc())
        .all()
    )
    member_ids = {m.user_id for m in memberships}
    creator = db.session.get(User, group.created_by)
    campus = db.session.get(Campus, group.campus_id)

    data = {
        "id": group.id,
        "name": group.name,
        "sport": group.sport,
        "description": group.description,
        "campus_id": group.campus_id,
        "campus_name": campus.name if campus else "",
        "campus_city": campus.city if campus else "",
        "created_by": group.created_by,
        "creator_username": creator.username if creator else "",
        "members_count": len(memberships),
        "is_member": bool(current_user_id and current_user_id in member_ids),
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }

    if include_members:
        members_payload = []
        for m in memberships:
            u = db.session.get(User, m.user_id)
            if u is not None:
                members_payload.append(
                    {
                        "user_id": u.id,
                        "username": u.username,
                        "avatar_url": u.avatar_url,
                        "level": u.level,
                        "favorite_sports": u.favorite_sports,
                        "role": m.role,
                        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                    }
                )
        data["members"] = members_payload
    return data
