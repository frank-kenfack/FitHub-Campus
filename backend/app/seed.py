"""Initialisation idempotente des donnees de reference FitHub Campus."""

import os

import bcrypt
from flask import current_app
from PIL import Image, ImageDraw

from app import create_app
from app.extensions import db
from app.models import (
    Badge,
    Campus,
    GroupMember,
    PlaceEvent,
    SportGroup,
    Story,
    StoryComment,
    StoryLike,
    User,
    Workout,
)

DEFAULT_CAMPUSES = [
    {
        "name": "Campus Lyon Gerland",
        "city": "Lyon",
        "latitude": 45.7299,
        "longitude": 4.8273,
    },
    {
        "name": "Campus Paris Nation",
        "city": "Paris",
        "latitude": 48.8483,
        "longitude": 2.3959,
    },
    {
        "name": "Campus Bordeaux Chartrons",
        "city": "Bordeaux",
        "latitude": 44.8569,
        "longitude": -0.5691,
    },
    {
        "name": "Campus Lille EuraTechnologies",
        "city": "Lille",
        "latitude": 50.6333,
        "longitude": 3.0196,
    },
]

DEFAULT_BADGES = [
    {
        "code": "first_workout",
        "name": "Premier Workout",
        "description": "Publie ta premiere seance ou story fitness.",
        "xp_reward": 50,
    },
    {
        "code": "five_workouts",
        "name": "5 Seances",
        "description": "Enchaine 5 entrainements valides sur FitHub.",
        "xp_reward": 120,
    },
    {
        "code": "fit_buddy_solidarity",
        "name": "Fit-Buddy Solidaire",
        "description": "Envoie des encouragements en direct a ton binome.",
        "xp_reward": 80,
    },
    {
        "code": "top_campus",
        "name": "Top Campus",
        "description": "Contribue a un defi inter-campus classe sur le podium.",
        "xp_reward": 150,
    },
    {
        "code": "event_participant",
        "name": "Participant Evenement",
        "description": "Confirme ta presence a un evenement sportif local.",
        "xp_reward": 75,
    },
]

DEMO_PASSWORD_HASH = bcrypt.hashpw(
    b"Password123!",
    bcrypt.gensalt(),
).decode("utf-8")


def _ensure_demo_story_image(
    upload_folder: str,
    filename: str,
    bg_rgb: tuple[int, int, int],
    accent_rgb: tuple[int, int, int],
    progress_ratio: float,
    variant: str,
) -> str:
    """Genere de maniere deterministe un visuel sportif illustre dans uploads/stories."""
    stories_dir = os.path.join(upload_folder, "stories")
    os.makedirs(stories_dir, exist_ok=True)
    full_path = os.path.join(stories_dir, filename)
    if not os.path.isfile(full_path):
        w, h = 800, 500
        img = Image.new("RGB", (w, h), bg_rgb)
        draw = ImageDraw.Draw(img)

        # Cercles decoratifs dynamiques
        draw.ellipse((460, -80, 880, 340), fill=accent_rgb)
        draw.ellipse((-90, 260, 260, 610), fill=(255, 255, 255))

        # Carte centrale graphique
        draw.rounded_rectangle((55, 65, 745, 435), radius=24, fill=(15, 23, 42))

        if variant == "run":
            # Trace GPS stylise
            pts = [(110, 330), (230, 250), (350, 290), (490, 175), (650, 210)]
            draw.line(pts, fill=accent_rgb, width=10)
            for px, py in pts:
                draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill=(255, 255, 255))
        elif variant == "bars":
            # Barres d'intensite street-workout
            heights = [110, 165, 210, 255, 230, 275]
            for idx, bh in enumerate(heights):
                x0 = 125 + idx * 92
                draw.rounded_rectangle(
                    (x0, 355 - bh, x0 + 56, 355),
                    radius=10,
                    fill=accent_rgb if idx >= 3 else (100, 116, 139),
                )
        else:
            # Silhouette / jauge comparative Avant vs Apres
            bar_x0, bar_x1 = 110, 690
            fill_x = int(bar_x0 + (bar_x1 - bar_x0) * progress_ratio)
            draw.rounded_rectangle(
                (bar_x0, 235, bar_x1, 295),
                radius=18,
                fill=(51, 65, 85),
            )
            draw.rounded_rectangle(
                (bar_x0, 235, fill_x, 295),
                radius=18,
                fill=accent_rgb,
            )
            # Anneau de forme
            cx = 230 if progress_ratio < 0.5 else 570
            draw.ellipse((cx - 68, 105, cx + 68, 215), outline=accent_rgb, width=12)

        # Barre inferieure de progression
        draw.rounded_rectangle((110, 375, 690, 398), radius=10, fill=(30, 41, 59))
        draw.rounded_rectangle(
            (110, 375, int(110 + 580 * progress_ratio), 398),
            radius=10,
            fill=(74, 222, 128) if progress_ratio > 0.7 else accent_rgb,
        )
        img.save(full_path, format="PNG", optimize=True)

    return f"/uploads/stories/{filename}"


def seed_database() -> dict:
    """Insere campus, badges, lieux, etudiants, groupes et publications de demo."""
    campus_map: dict[str, Campus] = {}

    for item in DEFAULT_CAMPUSES:
        campus = Campus.query.filter_by(name=item["name"]).first()
        if campus is None:
            campus = Campus(**item)
            db.session.add(campus)
            db.session.flush()
        campus_map[item["name"]] = campus

    for item in DEFAULT_BADGES:
        if Badge.query.filter_by(code=item["code"]).first() is None:
            db.session.add(Badge(**item))

    default_places = [
        {
            "campus_name": "Campus Lyon Gerland",
            "title": "Halle Sportive Tony Garnier Fit",
            "kind": "gym",
            "sport": "Musculation & Cardio",
            "description": "Salle partenaire etudiante avec tarif reduit.",
            "address": "24 Avenue Tony Garnier, 69007 Lyon",
            "latitude": 45.7318,
            "longitude": 4.8261,
        },
        {
            "campus_name": "Campus Paris Nation",
            "title": "Parc Street-Workout Vincennes",
            "kind": "spot",
            "sport": "Calisthenics",
            "description": "Aire de traction et barres paralleles en plein air.",
            "address": "Esplanade Saint-Louis, 75012 Paris",
            "latitude": 48.8428,
            "longitude": 2.4352,
        },
        {
            "campus_name": "Campus Bordeaux Chartrons",
            "title": "Quais Running Club Bordeaux",
            "kind": "spot",
            "sport": "Running",
            "description": "Parcours plat de 6 km le long de la Garonne.",
            "address": "Quai des Chartrons, 33000 Bordeaux",
            "latitude": 44.8535,
            "longitude": -0.5678,
        },
        {
            "campus_name": "Campus Lille EuraTechnologies",
            "title": "Basic-Fit Deule Campus",
            "kind": "gym",
            "sport": "Fitness & Cross-Training",
            "description": "Plateau cardio et poids libres a 4 min du campus.",
            "address": "165 Avenue de Bretagne, 59000 Lille",
            "latitude": 50.6347,
            "longitude": 3.0211,
        },
    ]

    for place in default_places:
        campus = campus_map[place["campus_name"]]
        exists = PlaceEvent.query.filter_by(
            title=place["title"],
            campus_id=campus.id,
        ).first()
        if exists is None:
            db.session.add(
                PlaceEvent(
                    campus_id=campus.id,
                    title=place["title"],
                    kind=place["kind"],
                    sport=place["sport"],
                    description=place["description"],
                    address=place["address"],
                    latitude=place["latitude"],
                    longitude=place["longitude"],
                )
            )

    demo_users_spec = [
        {
            "email": "ina.lyon@fithub.fr",
            "username": "InaFit_Lyon",
            "campus_name": "Campus Lyon Gerland",
            "bio": "Passionnee de semi-marathon et de renforcement musculaire.",
            "favorite_sports": "Running, Renforcement",
            "level": "Avance",
            "xp_points": 220,
        },
        {
            "email": "lucas.paris@fithub.fr",
            "username": "LucasBarz_Paris",
            "campus_name": "Campus Paris Nation",
            "bio": "Street-workout & tractions lestees apres les cours.",
            "favorite_sports": "Calisthenics, Cross-Training",
            "level": "Intermediaire",
            "xp_points": 160,
        },
        {
            "email": "sarah.bordeaux@fithub.fr",
            "username": "SarahRun_Bdx",
            "campus_name": "Campus Bordeaux Chartrons",
            "bio": "Sorties footing sur les quais et prepa HYROX.",
            "favorite_sports": "Running, Fitness",
            "level": "Intermediaire",
            "xp_points": 140,
        },
    ]

    user_map: dict[str, User] = {}
    for u_spec in demo_users_spec:
        user = User.query.filter_by(email=u_spec["email"]).first()
        if user is None:
            user = User(
                email=u_spec["email"],
                username=u_spec["username"],
                password_hash=DEMO_PASSWORD_HASH,
                campus_id=campus_map[u_spec["campus_name"]].id,
                bio=u_spec["bio"],
                favorite_sports=u_spec["favorite_sports"],
                level=u_spec["level"],
                xp_points=u_spec["xp_points"],
            )
            db.session.add(user)
            db.session.flush()
        user_map[u_spec["email"]] = user

    demo_groups_spec = [
        {
            "name": "Lyon Running Rhone",
            "sport": "Running",
            "description": "Sorties collectives mardi et jeudi 18h30 depuis Gerland.",
            "campus_name": "Campus Lyon Gerland",
            "creator_email": "ina.lyon@fithub.fr",
            "extra_members": ["sarah.bordeaux@fithub.fr"],
        },
        {
            "name": "Paris Street-Workout Nation",
            "sport": "Calisthenics",
            "description": "Sessions figures statiques, dips et muscle-ups tout niveau.",
            "campus_name": "Campus Paris Nation",
            "creator_email": "lucas.paris@fithub.fr",
            "extra_members": ["ina.lyon@fithub.fr"],
        },
        {
            "name": "Bordeaux Cross-Training B3",
            "sport": "Cross-Training",
            "description": "WOD d'equipe du vendredi midi pour preparer les defis campus.",
            "campus_name": "Campus Bordeaux Chartrons",
            "creator_email": "sarah.bordeaux@fithub.fr",
            "extra_members": [],
        },
    ]

    group_map: dict[str, SportGroup] = {}
    for g_spec in demo_groups_spec:
        campus = campus_map[g_spec["campus_name"]]
        creator = user_map[g_spec["creator_email"]]
        group = SportGroup.query.filter_by(
            name=g_spec["name"],
            campus_id=campus.id,
        ).first()
        if group is None:
            group = SportGroup(
                name=g_spec["name"],
                sport=g_spec["sport"],
                description=g_spec["description"],
                campus_id=campus.id,
                created_by=creator.id,
            )
            db.session.add(group)
            db.session.flush()
            db.session.add(
                GroupMember(group_id=group.id, user_id=creator.id, role="admin")
            )
            for extra_email in g_spec["extra_members"]:
                extra_user = user_map[extra_email]
                db.session.add(
                    GroupMember(
                        group_id=group.id,
                        user_id=extra_user.id,
                        role="member",
                    )
                )
        group_map[g_spec["name"]] = group

    # Publications sociales de demonstration (idempotentes)
    upload_dir = current_app.config.get("UPLOAD_FOLDER", "/app/uploads")
    ina = user_map["ina.lyon@fithub.fr"]
    lucas = user_map["lucas.paris@fithub.fr"]
    sarah = user_map["sarah.bordeaux@fithub.fr"]

    if Story.query.filter_by(user_id=ina.id, kind="workout_story").first() is None:
        run_media = _ensure_demo_story_image(
            upload_dir,
            "demo_ina_run.png",
            bg_rgb=(30, 46, 92),
            accent_rgb=(230, 26, 95),
            progress_ratio=0.82,
            variant="run",
        )
        w1 = Workout(
            user_id=ina.id,
            sport="Running",
            duration_minutes=48,
            calories=540,
            distance_km=9.4,
            source="story",
        )
        db.session.add(w1)
        db.session.flush()
        s1 = Story(
            user_id=ina.id,
            workout_id=w1.id,
            group_id=group_map["Lyon Running Rhone"].id,
            kind="workout_story",
            title="Fractionne Quais du Rhone",
            caption="Super rythme ce soir avec le groupe Lyon Running Rhone ! Objectif sub-45 min sur 10 km.",
            media_url=run_media,
            visibility="public",
        )
        db.session.add(s1)
        db.session.flush()
        db.session.add(StoryLike(story_id=s1.id, user_id=lucas.id))
        db.session.add(StoryLike(story_id=s1.id, user_id=sarah.id))
        db.session.add(
            StoryComment(
                story_id=s1.id,
                user_id=lucas.id,
                content="Solide l'allure a 5'06/km ! Bravo la team Lyon.",
            )
        )

    if Story.query.filter_by(user_id=lucas.id, kind="workout_story").first() is None:
        sw_media = _ensure_demo_story_image(
            upload_dir,
            "demo_lucas_sw.png",
            bg_rgb=(17, 24, 39),
            accent_rgb=(27, 138, 61),
            progress_ratio=0.76,
            variant="bars",
        )
        w2 = Workout(
            user_id=lucas.id,
            sport="Calisthenics",
            duration_minutes=60,
            calories=460,
            distance_km=0.0,
            source="story",
        )
        db.session.add(w2)
        db.session.flush()
        s2 = Story(
            user_id=lucas.id,
            workout_id=w2.id,
            group_id=group_map["Paris Street-Workout Nation"].id,
            kind="workout_story",
            title="Session Muscle-Ups & Dips Lestes",
            caption="5x5 muscle-ups stricts + dips a +20 kg au Parc de Vincennes.",
            media_url=sw_media,
            visibility="public",
        )
        db.session.add(s2)
        db.session.flush()
        db.session.add(StoryLike(story_id=s2.id, user_id=ina.id))

    if Story.query.filter_by(user_id=sarah.id, kind="before_after").first() is None:
        before_media = _ensure_demo_story_image(
            upload_dir,
            "demo_sarah_before.png",
            bg_rgb=(71, 85, 105),
            accent_rgb=(217, 119, 6),
            progress_ratio=0.34,
            variant="compare",
        )
        after_media = _ensure_demo_story_image(
            upload_dir,
            "demo_sarah_after.png",
            bg_rgb=(27, 138, 61),
            accent_rgb=(230, 26, 95),
            progress_ratio=0.92,
            variant="compare",
        )
        s3 = Story(
            user_id=sarah.id,
            group_id=group_map["Bordeaux Cross-Training B3"].id,
            kind="before_after",
            title="Progression Cardio & Gainage HYROX||10 semaines",
            caption="Passage de 32 min a 24 min sur le circuit 5 km + burpees grace aux seances collectives du vendredi !",
            before_media_url=before_media,
            after_media_url=after_media,
            visibility="public",
        )
        db.session.add(s3)
        db.session.flush()
        db.session.add(StoryLike(story_id=s3.id, user_id=ina.id))
        db.session.add(StoryLike(story_id=s3.id, user_id=lucas.id))
        db.session.add(
            StoryComment(
                story_id=s3.id,
                user_id=ina.id,
                content="Progression impressionnante en 10 semaines, bravo Sarah !",
            )
        )

    db.session.commit()
    return {
        "campuses": Campus.query.count(),
        "badges": Badge.query.count(),
        "places": PlaceEvent.query.count(),
        "users": User.query.count(),
        "groups": SportGroup.query.count(),
        "stories": Story.query.count(),
    }


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        counts = seed_database()
        print(f"Seed FitHub Campus termine : {counts}")
