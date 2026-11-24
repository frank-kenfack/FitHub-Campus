"""Routes Social Fitness (Etape 3) : Stories workouts, Avant/Apres, Likes & Commentaires."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import (
    GroupMember,
    SportGroup,
    Story,
    StoryComment,
    StoryLike,
    User,
    Workout,
)
from app.utils.gamification import evaluate_and_award_badges
from app.utils.media import remove_uploaded_file, save_validated_image
from app.utils.serializers import serialize_comment, serialize_story

social_bp = Blueprint("social", __name__, url_prefix="/api/social")


def _optional_uid() -> int | None:
    raw = get_jwt_identity()
    return int(raw) if raw is not None else None


def _user_group_ids(user_id: int | None) -> set[int]:
    if not user_id:
        return set()
    rows = GroupMember.query.filter_by(user_id=user_id).all()
    return {r.group_id for r in rows}


def _can_view_story(story: Story, user_id: int | None, member_group_ids: set[int]) -> bool:
    if story.visibility != "group":
        return True
    if not user_id or not story.group_id:
        return False
    return story.user_id == user_id or story.group_id in member_group_ids


@social_bp.get("/posts")
@jwt_required(optional=True)
def list_social_posts():
    """Liste les stories workouts et posts Avant/Apres selon filtres et visibilite."""
    uid = _optional_uid()
    member_gids = _user_group_ids(uid)

    kind = (request.args.get("kind") or "all").strip()
    timeframe = (request.args.get("timeframe") or "all").strip()
    campus_id = request.args.get("campus_id", type=int)
    group_id = request.args.get("group_id", type=int)

    query = Story.query
    if kind in {"workout_story", "before_after"}:
        query = query.filter(Story.kind == kind)
    if timeframe == "24h":
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        query = query.filter(Story.created_at >= cutoff)
    if campus_id is not None:
        query = query.join(User, User.id == Story.user_id).filter(
            User.campus_id == campus_id
        )
    if group_id is not None:
        query = query.filter(Story.group_id == group_id)

    stories = query.order_by(Story.created_at.desc(), Story.id.desc()).all()
    visible = [s for s in stories if _can_view_story(s, uid, member_gids)]

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    stories_24h_count = sum(
        1
        for s in visible
        if s.kind == "workout_story"
        and s.created_at
        and (
            s.created_at
            if s.created_at.tzinfo
            else s.created_at.replace(tzinfo=timezone.utc)
        )
        >= cutoff_24h
    )

    return (
        jsonify(
            {
                "posts": [serialize_story(s, current_user_id=uid) for s in visible],
                "stories_24h_count": stories_24h_count,
            }
        ),
        200,
    )


@social_bp.post("/stories")
@jwt_required()
def create_workout_story():
    """Publie une story de seance sportive avec photo compressee (US-3.1)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    sport = (request.form.get("sport") or "").strip()
    caption = (request.form.get("caption") or "").strip()
    title = (request.form.get("title") or "").strip()
    visibility = (request.form.get("visibility") or "public").strip()
    group_id_raw = request.form.get("group_id")

    try:
        duration_minutes = int(request.form.get("duration_minutes", "0"))
        calories = int(request.form.get("calories", "0") or 0)
        distance_km = float(request.form.get("distance_km", "0") or 0.0)
    except ValueError:
        return jsonify({"error": "Valeurs numeriques de seance invalides."}), 400

    if len(sport) < 2 or len(sport) > 60:
        return jsonify({"error": "La discipline sportive est requise."}), 400
    if duration_minutes <= 0 or duration_minutes > 1440:
        return jsonify({"error": "La duree doit etre comprise entre 1 et 1440 minutes."}), 400
    if calories < 0 or distance_km < 0:
        return jsonify({"error": "Calories et distance doivent etre positives."}), 400
    if visibility not in {"public", "group"}:
        return jsonify({"error": "Visibilite invalide (public ou group)."}), 400

    group_id: int | None = None
    if group_id_raw:
        try:
            group_id = int(group_id_raw)
        except ValueError:
            return jsonify({"error": "Identifiant de groupe invalide."}), 400
        if db.session.get(SportGroup, group_id) is None:
            return jsonify({"error": "Groupe sportif introuvable."}), 404
        is_member = (
            GroupMember.query.filter_by(group_id=group_id, user_id=user.id).first()
            is not None
        )
        if not is_member:
            return jsonify({"error": "Vous devez etre membre du groupe cible."}), 403
    elif visibility == "group":
        return jsonify({"error": "Un groupe doit etre choisi pour la visibilite groupe."}), 400

    try:
        media_url = save_validated_image(
            file_storage=request.files.get("image"),
            base_upload_folder=current_app.config["UPLOAD_FOLDER"],
            subfolder="stories",
            max_size=(1080, 1080),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    workout = Workout(
        user_id=user.id,
        sport=sport,
        duration_minutes=duration_minutes,
        calories=calories,
        distance_km=round(distance_km, 2),
        source="story",
    )
    db.session.add(workout)
    db.session.flush()

    story = Story(
        user_id=user.id,
        workout_id=workout.id,
        group_id=group_id,
        kind="workout_story",
        title=(title or f"Seance {sport}")[:140],
        caption=caption[:600],
        media_url=media_url,
        visibility=visibility,
    )
    user.xp_points = (user.xp_points or 0) + 25
    db.session.add(story)
    db.session.commit()
    evaluate_and_award_badges(user.id)

    return jsonify({"post": serialize_story(story, current_user_id=user.id)}), 201


@social_bp.post("/before-after")
@jwt_required()
def create_before_after_post():
    """Publie un comparatif photo Avant / Apres avec double upload (US-3.2)."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify({"error": "Utilisateur introuvable."}), 401

    title = (request.form.get("title") or "").strip()
    duration_label = (request.form.get("duration_label") or "").strip()
    caption = (request.form.get("caption") or "").strip()
    visibility = (request.form.get("visibility") or "public").strip()
    group_id_raw = request.form.get("group_id")

    if len(title) < 3 or len(title) > 100:
        return jsonify({"error": "Le titre doit contenir entre 3 et 100 caracteres."}), 400
    if visibility not in {"public", "group"}:
        return jsonify({"error": "Visibilite invalide (public ou group)."}), 400

    group_id: int | None = None
    if group_id_raw:
        try:
            group_id = int(group_id_raw)
        except ValueError:
            return jsonify({"error": "Identifiant de groupe invalide."}), 400
        if db.session.get(SportGroup, group_id) is None:
            return jsonify({"error": "Groupe sportif introuvable."}), 404
        is_member = (
            GroupMember.query.filter_by(group_id=group_id, user_id=user.id).first()
            is not None
        )
        if not is_member:
            return jsonify({"error": "Vous devez etre membre du groupe cible."}), 403
    elif visibility == "group":
        return jsonify({"error": "Un groupe doit etre choisi pour la visibilite groupe."}), 400

    before_url = ""
    try:
        before_url = save_validated_image(
            file_storage=request.files.get("before_image"),
            base_upload_folder=current_app.config["UPLOAD_FOLDER"],
            subfolder="stories",
            max_size=(1080, 1080),
        )
        after_url = save_validated_image(
            file_storage=request.files.get("after_image"),
            base_upload_folder=current_app.config["UPLOAD_FOLDER"],
            subfolder="stories",
            max_size=(1080, 1080),
        )
    except ValueError as exc:
        if before_url:
            remove_uploaded_file(before_url, current_app.config["UPLOAD_FOLDER"])
        return jsonify({"error": str(exc)}), 400

    clean_title = title.replace("||", " ")
    clean_duration = duration_label.replace("||", " ")[:32]
    encoded_title = (
        f"{clean_title}||{clean_duration}"[:140] if clean_duration else clean_title[:140]
    )

    story = Story(
        user_id=user.id,
        group_id=group_id,
        kind="before_after",
        title=encoded_title,
        caption=caption[:600],
        before_media_url=before_url,
        after_media_url=after_url,
        visibility=visibility,
    )
    user.xp_points = (user.xp_points or 0) + 35
    db.session.add(story)
    db.session.commit()
    evaluate_and_award_badges(user.id)

    return jsonify({"post": serialize_story(story, current_user_id=user.id)}), 201


@social_bp.delete("/posts/<int:post_id>")
@jwt_required()
def delete_social_post(post_id: int):
    """Supprime une publication (reserve exclusivement a son auteur) et nettoie ses medias."""
    uid = int(get_jwt_identity())
    story = db.session.get(Story, post_id)
    if story is None:
        return jsonify({"error": "Publication introuvable."}), 404
    if story.user_id != uid:
        return jsonify({"error": "Seul l'auteur peut supprimer cette publication."}), 403

    media_to_clean = [story.media_url, story.before_media_url, story.after_media_url]
    workout = db.session.get(Workout, story.workout_id) if story.workout_id else None

    db.session.delete(story)
    if workout is not None and workout.source == "story":
        db.session.delete(workout)
    db.session.commit()

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    for url in media_to_clean:
        if url:
            remove_uploaded_file(url, upload_folder)

    return jsonify({"deleted": True, "post_id": post_id}), 200


@social_bp.post("/posts/<int:post_id>/like")
@jwt_required()
def like_or_toggle_post(post_id: int):
    """Ajoute, retire ou bascule un like de maniere idempotente (US-3.3)."""
    uid = int(get_jwt_identity())
    story = db.session.get(Story, post_id)
    if story is None:
        return jsonify({"error": "Publication introuvable."}), 404
    if not _can_view_story(story, uid, _user_group_ids(uid)):
        return jsonify({"error": "Acces non autorise a cette publication."}), 403

    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "toggle").strip().lower()

    existing = StoryLike.query.filter_by(story_id=story.id, user_id=uid).first()
    if action == "like":
        if existing is None:
            db.session.add(StoryLike(story_id=story.id, user_id=uid))
            db.session.commit()
        liked = True
    elif action == "unlike":
        if existing is not None:
            db.session.delete(existing)
            db.session.commit()
        liked = False
    else:
        if existing is None:
            db.session.add(StoryLike(story_id=story.id, user_id=uid))
            liked = True
        else:
            db.session.delete(existing)
            liked = False
        db.session.commit()

    likes_count = StoryLike.query.filter_by(story_id=story.id).count()
    return (
        jsonify(
            {
                "liked": liked,
                "likes_count": likes_count,
                "post_id": story.id,
            }
        ),
        200,
    )


@social_bp.get("/posts/<int:post_id>/comments")
@jwt_required(optional=True)
def list_post_comments(post_id: int):
    """Liste les commentaires d'une publication sociale."""
    uid = _optional_uid()
    story = db.session.get(Story, post_id)
    if story is None:
        return jsonify({"error": "Publication introuvable."}), 404
    if not _can_view_story(story, uid, _user_group_ids(uid)):
        return jsonify({"error": "Acces non autorise a cette publication."}), 403

    comments = (
        StoryComment.query.filter_by(story_id=story.id)
        .order_by(StoryComment.created_at.asc(), StoryComment.id.asc())
        .all()
    )
    return jsonify({"comments": [serialize_comment(c) for c in comments]}), 200


@social_bp.post("/posts/<int:post_id>/comments")
@jwt_required()
def add_post_comment(post_id: int):
    """Ajoute un commentaire sur une story ou photo Avant/Apres (US-3.3)."""
    uid = int(get_jwt_identity())
    story = db.session.get(Story, post_id)
    if story is None:
        return jsonify({"error": "Publication introuvable."}), 404
    if not _can_view_story(story, uid, _user_group_ids(uid)):
        return jsonify({"error": "Acces non autorise a cette publication."}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content or len(content) > 500:
        return jsonify({"error": "Le commentaire doit contenir entre 1 et 500 caracteres."}), 400

    comment = StoryComment(story_id=story.id, user_id=uid, content=content)
    db.session.add(comment)
    db.session.commit()

    total = StoryComment.query.filter_by(story_id=story.id).count()
    return (
        jsonify(
            {
                "comment": serialize_comment(comment),
                "comments_count": total,
            }
        ),
        201,
    )


@social_bp.delete("/comments/<int:comment_id>")
@jwt_required()
def delete_post_comment(comment_id: int):
    """Supprime un commentaire (autorise a son auteur ou a l'auteur du post)."""
    uid = int(get_jwt_identity())
    comment = db.session.get(StoryComment, comment_id)
    if comment is None:
        return jsonify({"error": "Commentaire introuvable."}), 404

    story = db.session.get(Story, comment.story_id)
    if comment.user_id != uid and (story is None or story.user_id != uid):
        return jsonify({"error": "Suppression non autorisee."}), 403

    story_id = comment.story_id
    db.session.delete(comment)
    db.session.commit()

    total = StoryComment.query.filter_by(story_id=story_id).count()
    return (
        jsonify(
            {
                "deleted": True,
                "comment_id": comment_id,
                "comments_count": total,
            }
        ),
        200,
    )
