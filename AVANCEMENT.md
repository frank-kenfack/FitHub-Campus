# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-05/fitbuddy-realtime`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-05/fitbuddy-realtime)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 5 / 8 étapes validées (62,5 %)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `pytest` 5/5 |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 14/14 |
| **3** | [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness) | Stories workouts (< 24h), partage photos Avant/Après (slider comparatif), likes & commentaires | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 22/22 |
| **4** | [`step-04/defis-classements`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-04/defis-classements) | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 30/30 |
| **5** | [`step-05/fitbuddy-realtime`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-05/fitbuddy-realtime) | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ✅ Validée (attente revue) | `ruff` OK • `pytest` **37/37** (0 warning) • WebSocket live 2 navigateurs vérifié |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import JSON/GPX | ⏳ À faire | — |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 5 — `step-05/fitbuddy-realtime`

### Livrables implémentés
- **Matching & Gestion Fit-Buddy (`US-5.1` — `backend/app/routes/buddies.py`)** :
  - `GET /api/buddies/discover` : recherche filtrable par `campus_id`, `sport`, `level` et mot-clé, avec calcul d'un **score d'affinité (`compatibility_score` sur 100 %)**.
  - `GET /api/buddies`, `POST /api/buddies/request` & `POST /api/buddies/<id>/respond` : workflow complet `pending` → `accepted` / `declined`, notifications temps réel (`buddy_request`, `buddy_updated`) et bonus `+25 XP` à l'acceptation.
- **Encouragements mutuels en temps réel (`US-5.2` — `backend/app/sockets.py`, `backend/app/utils/buddies_service.py`)** :
  - Authentification WebSocket par jeton JWT (`connect` → abonnement automatique à la room privée `user_<id>`) et intégration du broker **Redis 7** (`message_queue=REDIS_URL`).
  - Événement `send_encouragement` + fallback REST `GET/POST /api/buddies/<partner_id>/encouragements` : diffusion instantanée `new_encouragement` vers les deux sessions et conservation de l'historique en PostgreSQL.
- **Compteur de régularité partagé (`US-5.3`)** :
  - Calcul dynamique `compute_pair_streak_days` sur les jours consécutifs d'activité (`Workout`, `Story`, `Encouragement`) affiché sur la carte du binôme (`🔥 X j streak`).
- **Interface React Temps Réel (`frontend/src/components/FitBuddyView.jsx`)** :
  - Intégration `socket.io-client` à travers le reverse proxy WebSocket Nginx (`/socket.io`), témoin d'état `🟢 Live WebSocket Connecté`, boutons d'encouragements 1-clic, messagerie en direct avec toast temps réel et explorateur d'affinité.

### Résultats des vérifications
- **`ruff check app tests wsgi.py gunicorn_wsgi.py`** : `All checks passed!`
- **`pytest -v`** : **`37 passed in 23.85s`** (0 warning — Étapes 1 à 5, incluant `test_realtime_websocket_delivery_between_two_sessions` et `test_websocket_rejects_unauthenticated_or_forged_token`).
- **Test E2E 2 Navigateurs Simultanés via Nginx (`:8080`)** : session Chrome B (`SarahRun_Bdx`) envoie un encouragement WebSocket → session Chrome A (`InaFit_Lyon`) affiche instantanément le toast et la bulle sans rechargement.
