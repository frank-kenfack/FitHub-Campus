# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 3 / 8 étapes validées (37,5 %)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `ruff` OK • `pytest` 5/5 • Persistance `down`/`up` OK |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 14/14 • Persistance avatar OK |
| **3** | [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness) | Stories workouts (< 24h), partage photos Avant/Après (slider comparatif), likes & commentaires | ✅ Validée (attente revue) | `ruff` OK • `pytest` **22/22** (0 warning) • Médias `/uploads/stories/` servis en `200 OK` |
| **4** | `step-04/defis-classements` | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ⏳ À faire | — |
| **5** | `step-05/fitbuddy-realtime` | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ⏳ À faire | — |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import JSON/GPX | ⏳ À faire | — |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 3 — `step-03/social-fitness`

### Livrables implémentés
- **API Social Fitness (`backend/app/routes/social.py`, `backend/app/utils/serializers.py`)** :
  - `GET /api/social/posts` : fil communautaire filtrable par type (`workout_story` / `before_after`), fenêtre temporelle (`timeframe=24h`), `campus_id` et `group_id`, avec contrôle strict des publications privées de groupe (`visibility="group"`).
  - `POST /api/social/stories` (`US-3.1`) : création simultanée de l'enregistrement `Workout` (sport, durée, distance, calories) et de la `Story` avec compression/validation Pillow (`1080x1080`) sur le volume persistant `uploads_data` (+25 XP).
  - `POST /api/social/before-after` (`US-3.2`) : double upload validé (`before_image` + `after_image`), durée d'évolution et visibilité publique ou groupe (+35 XP).
  - `DELETE /api/social/posts/<id>` (`US-3.2`) : suppression réservée exclusivement à l'auteur (`403` sinon) + nettoyage physique des fichiers médias sur le disque.
  - `POST /api/social/posts/<id>/like` & `GET/POST /api/social/posts/<id>/comments` & `DELETE /api/social/comments/<id>` (`US-3.3`) : likes idempotents (toggle ou explicites `like`/`unlike`) et commentaires temps réel côté client.
- **Interface React Social Fitness (`frontend/src/components/SocialFeedView.jsx`)** :
  - Carrousel supérieur des **Stories Workouts < 24h** avec visionneuse rapide au clic.
  - Composant interactif **`BeforeAfterComparator`** offrant un **curseur glissant Avant/Après** (`clip-path` sans déformation) et une bascule **Vue Côte à côte**.
  - Formulaires de publication (Story Workout & Avant/Après) et interactions sociales instantanées (applaudissements + commentaires sans rechargement).

### Résultats des vérifications
- **`ruff check app tests wsgi.py gunicorn_wsgi.py`** : `All checks passed!`
- **`pytest -v`** : **`22 passed in 13.72s`** (0 warning — 5 tests Étape 1 + 9 tests Étape 2 + 8 nouveaux tests Étape 3 dans `tests/test_step03_social.py`).
- **Médias servis via Nginx (`:8080`)** : toutes les images `/uploads/stories/...` répondent `200 OK` (`image/png`).

---

## Historique des étapes fusionnées dans `develop`
- **Étape 1 (`step-01/socle-docker`)** : Stack Docker 4 conteneurs, 16 tables + migrations Alembic, seed, `/api/health`, 5/5 `pytest`.
- **Étape 2 (`step-02/auth-profils-groupes`)** : Auth JWT (`bcrypt`), profils + upload avatar persistant, groupes sportifs, 14/14 `pytest`.
