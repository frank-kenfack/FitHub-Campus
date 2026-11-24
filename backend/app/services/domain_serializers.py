"""Serialisation JSON des entites utilisateurs, groupes et publications."""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import (
    Badge,
    Campus,
    GroupMember,
    SportGroup,
    Story,
    StoryComment,
    StoryLike,
    User,
    UserBadge,
    Workout,
)


def serialize_user(user: User, include_stats: bool = False) -> dict:
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
        badges_xp = sum(int(b.xp_reward or 0) for b in awarded)
        payload["stats"] = {
            "workouts_count": workouts_count,
            "groups_count": groups_count,
            "badges_count": len(awarded),
            "xp_points": user.xp_points,
            "badges_xp": badges_xp,
            "total_xp": int(user.xp_points or 0) + badges_xp,
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
    memberships = (
        GroupMember.query.filter_by(group_id=group.id)
        .order_by(GroupMember.joined_at.asc())
        .all()
    )
    member_ids = {m.user_id for m in memberships}
    creator = db.session.get(User, group.created_by)
    campus = db.session.get(Campus, group.campus_id)

    group_payload = {
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
        group_payload["members"] = members_payload
    return group_payload


def serialize_comment(comment: StoryComment) -> dict:
    author = db.session.get(User, comment.user_id)
    campus = db.session.get(Campus, author.campus_id) if author else None
    return {
        "id": comment.id,
        "story_id": comment.story_id,
        "user_id": comment.user_id,
        "username": author.username if author else "Etudiant",
        "avatar_url": author.avatar_url if author else "",
        "campus_name": campus.name if campus else "",
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


def serialize_story(story: Story, current_user_id: int | None = None) -> dict:
    author = db.session.get(User, story.user_id)
    campus = db.session.get(Campus, author.campus_id) if author else None
    workout = db.session.get(Workout, story.workout_id) if story.workout_id else None
    group = db.session.get(SportGroup, story.group_id) if story.group_id else None

    raw_title = story.title or ""
    if "||" in raw_title:
        clean_title, duration_label = raw_title.split("||", 1)
    else:
        clean_title, duration_label = raw_title, ""

    likes_count = StoryLike.query.filter_by(story_id=story.id).count()
    is_liked = False
    if current_user_id:
        is_liked = (
            StoryLike.query.filter_by(
                story_id=story.id,
                user_id=current_user_id,
            ).first()
            is not None
        )

    comments = (
        StoryComment.query.filter_by(story_id=story.id)
        .order_by(StoryComment.created_at.asc(), StoryComment.id.asc())
        .all()
    )

    now_utc = datetime.now(timezone.utc)
    created_utc = story.created_at
    if created_utc and created_utc.tzinfo is None:
        created_utc = created_utc.replace(tzinfo=timezone.utc)
    is_fresh_24h = bool(created_utc and (now_utc - created_utc) <= timedelta(hours=24))

    payload = {
        "id": story.id,
        "kind": story.kind,
        "title": clean_title,
        "duration_label": duration_label,
        "caption": story.caption,
        "media_url": story.media_url,
        "before_media_url": story.before_media_url,
        "after_media_url": story.after_media_url,
        "visibility": story.visibility,
        "group_id": story.group_id,
        "group_name": group.name if group else "",
        "user_id": story.user_id,
        "username": author.username if author else "Etudiant",
        "avatar_url": author.avatar_url if author else "",
        "campus_id": campus.id if campus else None,
        "campus_name": campus.name if campus else "",
        "likes_count": likes_count,
        "is_liked": is_liked,
        "comments_count": len(comments),
        "comments": [serialize_comment(c) for c in comments],
        "is_fresh_24h": is_fresh_24h,
        "created_at": story.created_at.isoformat() if story.created_at else None,
        "workout": None,
    }
    if workout is not None:
        payload["workout"] = {
            "id": workout.id,
            "sport": workout.sport,
            "duration_minutes": workout.duration_minutes,
            "calories": workout.calories,
            "distance_km": workout.distance_km,
        }
    return payload
