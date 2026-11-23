"""Initialisation idempotente des donnees de reference FitHub Campus."""

from app import create_app
from app.extensions import db
from app.models import Badge, Campus, PlaceEvent

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


def seed_database() -> dict:
    """Insere campus, badges et lieux initiaux sans creer de doublons."""
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

    db.session.commit()
    return {
        "campuses": Campus.query.count(),
        "badges": Badge.query.count(),
        "places": PlaceEvent.query.count(),
    }


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        counts = seed_database()
        print(f"Seed FitHub Campus termine : {counts}")
