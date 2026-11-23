# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 1 / 8 étapes validées (12,5 %)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Validée (attente revue) | 4 conteneurs `healthy` • `ruff` OK • `pytest` 5/5 • Persistance `down`/`up` OK • Non-root OK |
| **2** | `step-02/auth-profils-groupes` | Auth JWT sécurisée (bcrypt), profils + upload avatar persistant, groupes sportifs | ⏳ À faire | — |
| **3** | `step-03/social-fitness` | Stories workouts, partage photos Avant/Après (slider comparatif), likes & commentaires | ⏳ À faire | — |
| **4** | `step-04/defis-classements` | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ⏳ À faire | — |
| **5** | `step-05/fitbuddy-realtime` | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ⏳ À faire | — |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import JSON/GPX | ⏳ À faire | — |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 1 — `step-01/socle-docker`

### Livrables implémentés
- **Infra & Config racine** : `docker-compose.yml` (4 services + réseau privé `fithub_net` + 2 volumes persistants `postgres_data` et `uploads_data`), `.env.example`, `.gitignore`, `README.md`.
- **Backend (`backend/`)** :
  - `Dockerfile` multi-stage Python 3.12-slim exécuté en utilisateur non-root (`appuser`, `uid=999`) + `entrypoint.sh` (migrations + seed + Gunicorn/Eventlet).
  - `app/models.py` : 16 tables relationnelles avec clés étrangères et contraintes d'unicité (`campuses`, `users`, `groups`, `group_members`, `workouts`, `stories`, `story_likes`, `story_comments`, `challenges`, `challenge_entries`, `fit_buddies`, `encouragements`, `places_events`, `event_rsvps`, `badges`, `user_badges`).
  - `migrations/versions/b7ed6f971fa6_initial_schema.py` : migration Alembic initiale générée et appliquée.
  - `app/seed.py` : seed idempotent (4 campus étudiants, 5 badges de base, 4 lieux sportifs).
  - `app/routes/health.py` : `GET /api/health` (statut PostgreSQL + Redis + compteurs) et `GET /api/campuses`.
  - `tests/test_step01_socle.py` : 5 tests automatisés.
- **Frontend (`frontend/`)** :
  - `Dockerfile` multi-stage (`node:20-alpine` → `nginxinc/nginx-unprivileged:1.27-alpine`, `uid=101`).
  - `nginx.conf` : proxy `/api/`, `/uploads/`, `/socket.io/` (WebSocket) + endpoint `/nginx-health`.
  - `src/App.jsx` & `src/styles/global.css` : interface *mobile-first* responsive (navigation basse mobile + barre desktop) affichant le diagnostic live et les campus depuis PostgreSQL.

### Résultats des vérifications
- **`docker compose ps`** : `fithub-db`, `fithub-redis`, `fithub-backend`, `fithub-frontend` tous en `Up (healthy)`.
- **`ruff check app tests wsgi.py gunicorn_wsgi.py`** : `All checks passed!`
- **`pytest -v`** : `5 passed in 1.29s` (`test_health_endpoint_ok`, `test_all_mvp_tables_created`, `test_seed_is_idempotent`, `test_campuses_endpoint_returns_seeded_data`, `test_foreign_key_integrity_enforced`).
- **Endpoints HTTP via Nginx (`localhost:8080`)** :
  - `GET /api/health` → `200 OK` (`database: ok`, `redis: ok`, `campuses: 4`, `badges: 5`, `places: 4`)
  - `GET /api/campuses` → `200 OK` (4 campus)
  - `GET /` → `200 OK` (`FitHub Campus`)
- **Persistance PostgreSQL** : insertion d'un campus témoin → `docker compose down` (sans `-v`) → `docker compose up -d --wait` → ligne toujours présente en base → nettoyage confirmé (`4` campus).
- **Sécurité** : conteneurs backend (`uid=999(appuser)`) et frontend (`uid=101(nginx)`) non-root ; `0` occurrence de jeton dans `.git/config` et le workspace.
