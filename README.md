# FitHub Campus — Réseau Social Fitness Étudiant

Application cloud-native *mobile-first* permettant aux étudiants de créer des groupes sportifs, relever des défis inter-campus, trouver un *fit-buddy* avec encouragements temps réel, découvrir des salles et événements géolocalisés et débloquer des badges.

---

## Architecture (Stack 4 conteneurs Docker)

| Service | Image / Technologie | Rôle | Port / Réseau |
| :--- | :--- | :--- | :--- |
| **`frontend`** | React 18 (Vite) + Nginx unprivileged | Interface *mobile-first* responsive + reverse proxy `/api`, `/uploads`, `/socket.io` | `8080` (exposé) |
| **`backend`** | Python 3.12 + Flask + Gunicorn/Eventlet | API REST, migrations Alembic, Socket.IO temps réel | `5000` (exposé) |
| **`db`** | PostgreSQL 16 Alpine | Persistance relationnelle (16 tables métier) | `5432` (interne `fithub_net`) |
| **`redis`** | Redis 7 Alpine | Broker Socket.IO & cache | `6379` (interne `fithub_net`) |

Volumes persistants nommés : `postgres_data` (données PostgreSQL) et `uploads_data` (avatars, stories et médias).

---

## Démarrage rapide

```bash
cp .env.example .env
docker compose up --build -d
```

- Application Web & Proxy : http://localhost:8080
- API Healthcheck : http://localhost:8080/api/health
- Campus seedés : http://localhost:8080/api/campuses

---

## Tests et qualité (dans les conteneurs)

```bash
# Lint backend
docker compose exec -T backend ruff check app tests

# Tests unitaires et d'intégration
docker compose exec -T backend pytest -v
```

---

## Workflow Git & Suivi par étapes

- `main` : version stable / livrable final
- `develop` : branche d'intégration des étapes validées
- `step-XX/...` : une branche dédiée par étape, validée par tests et revue visuelle avant fusion

Consultez le journal [AVANCEMENT.md](./AVANCEMENT.md), l'album des captures [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md) ou ouvrez [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html) dans votre navigateur pour suivre l'avancement détaillé.
