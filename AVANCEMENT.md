# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 2 / 8 étapes validées (25 %)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `ruff` OK • `pytest` 5/5 • Persistance `down`/`up` OK |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Validée (attente revue) | `ruff` OK • `pytest` **14/14** (0 warning) • Upload & persistance avatar après restart OK |
| **3** | `step-03/social-fitness` | Stories workouts, partage photos Avant/Après (slider comparatif), likes & commentaires | ⏳ À faire | — |
| **4** | `step-04/defis-classements` | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ⏳ À faire | — |
| **5** | `step-05/fitbuddy-realtime` | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ⏳ À faire | — |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import JSON/GPX | ⏳ À faire | — |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 2 — `step-02/auth-profils-groupes`

### Livrables implémentés
- **Authentification JWT & Sécurité (`backend/app/routes/auth.py`)** :
  - `POST /api/auth/register` : validation email/pseudo/campus, hachage mot de passe `bcrypt` (`$2b$`), émission jeton JWT RFC 7518.
  - `POST /api/auth/login` & `GET /api/auth/me` : vérification d'identifiants et gestionnaire d'erreurs JWT retournant systématiquement `401` sur accès non authentifié ou jeton invalide.
- **Profils sportifs & Avatar persistant (`backend/app/routes/users.py`, `backend/app/utils/media.py`)** :
  - `GET /api/users/me`, `PUT /api/users/me`, `GET /api/users/<id>` : lecture/modification du profil sportif (pseudo, campus, sports favoris, niveau, bio) et statistiques personnelles (`xp_points`, `groups_count`, `workouts_count`, `badges_count`).
  - `POST /api/users/me/avatar` : validation réelle de l'image via Pillow (`JPEG`, `PNG`, `WEBP`), redimensionnement (`400x400`), stockage sur le volume persistant `/app/uploads/avatars/` et exposition via `/uploads/<path>` derrière Nginx.
- **Groupes sportifs (`backend/app/routes/groups.py`)** :
  - `GET /api/groups` (filtres `campus_id`, `sport`, recherche `q`), `GET /api/groups/<id>` (liste détaillée des membres et rôles), `POST /api/groups`, `PUT /api/groups/<id>`, `DELETE /api/groups/<id>` (contrôle créateur `403`), `POST /api/groups/<id>/join` et `POST /api/groups/<id>/leave`.
- **Seed enrichi (`backend/app/seed.py`)** : 3 comptes étudiants de démo (`InaFit_Lyon`, `LucasBarz_Paris`, `SarahRun_Bdx`) et 3 groupes sportifs pré-remplis.
- **Interface React Mobile-First (`frontend/src/`)** :
  - `src/api.js` (client HTTP JWT), `src/components/AuthProfileView.jsx` (Connexion / Inscription + connexion démo 1-clic + édition profil + upload d'avatar), `src/components/GroupsView.jsx` (filtres campus/sport/recherche, création de groupe, adhésion/désinscription, tiroir des membres).

### Résultats des vérifications
- **`ruff check app tests wsgi.py gunicorn_wsgi.py`** : `All checks passed!`
- **`pytest -v`** : **`14 passed in 7.26s`** (0 warning — 5 tests Étape 1 + 9 nouveaux tests Étape 2 dans `tests/test_step02_auth_groups.py`).
- **Persistance `uploads_data` via Nginx (`:8080`)** : connexion `InaFit_Lyon` → upload `ina_avatar.png` → `docker compose restart backend` → `GET http://localhost:8080/uploads/avatars/...` renvoie toujours `200 OK` (`image/png`).

---

## Historique — Étape 1 (`step-01/socle-docker`) — Fusionnée dans `develop`
- Stack Docker 4 conteneurs (`frontend`, `backend`, `db`, `redis`), 16 tables SQLAlchemy + migration Alembic initiale, seed idempotent, `/api/health` & `/api/campuses`, 5/5 tests `pytest`.
