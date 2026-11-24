"""Initialisation idempotente des donnees de reference FitHub Campus."""

import bcrypt

from app import create_app
from app.extensions import db
from app.models import Badge, Campus, GroupMember, PlaceEvent, SportGroup, User

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


def seed_database() -> dict:
    """Insere campus, badges, lieux, etudiants et groupes de demo sans doublons."""
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

    db.session.commit()
    return {
        "campuses": Campus.query.count(),
        "badges": Badge.query.count(),
        "places": PlaceEvent.query.count(),
        "users": User.query.count(),
        "groups": SportGroup.query.count(),
    }


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        counts = seed_database()
        print(f"Seed FitHub Campus termine : {counts}")
