"""Modeles SQLAlchemy du domaine FitHub Campus (16 tables MVP)."""

from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    """Retourne l'horodatage courant en UTC avec fuseau horaire."""
    return datetime.now(timezone.utc)


class Campus(db.Model):
    """Etablissement ou campus etudiant partenaire."""

    __tablename__ = "campuses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        """Serialise un campus au format JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class User(db.Model):
    """Compte etudiant inscrit sur FitHub Campus."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    campus_id = db.Column(
        db.Integer,
        db.ForeignKey("campuses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bio = db.Column(db.Text, default="", nullable=False)
    avatar_url = db.Column(db.String(255), default="", nullable=False)
    favorite_sports = db.Column(db.String(255), default="Fitness", nullable=False)
    level = db.Column(db.String(40), default="Intermediaire", nullable=False)
    xp_points = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    campus = db.relationship("Campus", backref=db.backref("users", lazy=True))


class SportGroup(db.Model):
    """Groupe sportif cree par les etudiants d'un campus."""

    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sport = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    campus_id = db.Column(
        db.Integer,
        db.ForeignKey("campuses.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class GroupMember(db.Model):
    """Appartenance d'un etudiant a un groupe sportif."""

    __tablename__ = "group_members"
    __table_args__ = (
        db.UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = db.Column(db.String(30), default="member", nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Workout(db.Model):
    """Seance de sport enregistree ou importee."""

    __tablename__ = "workouts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    sport = db.Column(db.String(60), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    calories = db.Column(db.Integer, default=0, nullable=False)
    distance_km = db.Column(db.Float, default=0.0, nullable=False)
    source = db.Column(db.String(40), default="manual", nullable=False)
    performed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Story(db.Model):
    """Publication sociale (story workout ou duo avant/apres)."""

    __tablename__ = "stories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workout_id = db.Column(
        db.Integer,
        db.ForeignKey("workouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind = db.Column(db.String(30), default="workout_story", nullable=False)
    title = db.Column(db.String(140), default="", nullable=False)
    caption = db.Column(db.Text, default="", nullable=False)
    media_url = db.Column(db.String(255), default="", nullable=False)
    before_media_url = db.Column(db.String(255), default="", nullable=False)
    after_media_url = db.Column(db.String(255), default="", nullable=False)
    visibility = db.Column(db.String(20), default="public", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class StoryLike(db.Model):
    """Like ou applaudissement unique par utilisateur et publication."""

    __tablename__ = "story_likes"
    __table_args__ = (
        db.UniqueConstraint("story_id", "user_id", name="uq_story_like"),
    )

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(
        db.Integer,
        db.ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class StoryComment(db.Model):
    """Commentaire sur une story ou photo avant/apres."""

    __tablename__ = "story_comments"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(
        db.Integer,
        db.ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Challenge(db.Model):
    """Defi sportif inter-campus avec objectif chiffre."""

    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    sport = db.Column(db.String(60), nullable=False)
    target_value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )


class ChallengeEntry(db.Model):
    """Participation et score cumule d'un etudiant pour son campus."""

    __tablename__ = "challenge_entries"
    __table_args__ = (
        db.UniqueConstraint("challenge_id", "user_id", name="uq_challenge_entry"),
    )

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    campus_id = db.Column(
        db.Integer,
        db.ForeignKey("campuses.id", ondelete="CASCADE"),
        nullable=False,
    )
    score = db.Column(db.Float, default=0.0, nullable=False)
    proof_media_url = db.Column(db.String(255), default="", nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class FitBuddy(db.Model):
    """Relation de binome sportif (matching fit-buddy)."""

    __tablename__ = "fit_buddies"
    __table_args__ = (
        db.UniqueConstraint("requester_id", "addressee_id", name="uq_fit_buddy_pair"),
    )

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    addressee_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.String(20), default="pending", nullable=False)
    streak_days = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Encouragement(db.Model):
    """Message ou encouragement temps reel entre fit-buddies."""

    __tablename__ = "encouragements"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message = db.Column(db.String(280), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class PlaceEvent(db.Model):
    """Salle de sport, spot street-workout ou evenement geolocalise."""

    __tablename__ = "places_events"

    id = db.Column(db.Integer, primary_key=True)
    campus_id = db.Column(
        db.Integer,
        db.ForeignKey("campuses.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = db.Column(db.String(140), nullable=False)
    kind = db.Column(db.String(30), default="gym", nullable=False)
    sport = db.Column(db.String(60), default="Fitness", nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    address = db.Column(db.String(200), default="", nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    max_participants = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class EventRsvp(db.Model):
    """Confirmation de participation d'un etudiant a un evenement."""

    __tablename__ = "event_rsvps"
    __table_args__ = (
        db.UniqueConstraint("event_id", "user_id", name="uq_event_rsvp"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("places_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Badge(db.Model):
    """Definition d'un badge ou achievement de gamification."""

    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    xp_reward = db.Column(db.Integer, default=50, nullable=False)


class UserBadge(db.Model):
    """Attribution unique d'un badge a un utilisateur."""

    __tablename__ = "user_badges"
    __table_args__ = (
        db.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    badge_id = db.Column(
        db.Integer,
        db.ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
    )
    awarded_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
