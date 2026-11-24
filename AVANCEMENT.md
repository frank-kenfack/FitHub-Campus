# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-04/defis-classements`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-04/defis-classements)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 4 / 8 étapes validées (50 %)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `pytest` 5/5 |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 14/14 |
| **3** | [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness) | Stories workouts (< 24h), partage photos Avant/Après (slider comparatif), likes & commentaires | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 22/22 |
| **4** | [`step-04/defis-classements`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-04/defis-classements) | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ✅ Validée (attente revue) | `ruff` OK • `pytest` **30/30** (0 warning) • Podiums 4 campus actifs |
| **5** | `step-05/fitbuddy-realtime` | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ⏳ À faire | — |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import JSON/GPX | ⏳ À faire | — |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 4 — `step-04/defis-classements`

### Livrables implémentés
- **API Défis Inter-Campus & Classements (`backend/app/routes/challenges.py`)** :
  - `GET /api/challenges` & `POST /api/challenges` & `DELETE /api/challenges/<id>` (`US-4.1`) : création de défis inter-écoles (objectif chiffré, unité, durée/dates), filtres `status=active|completed|all` et `sport`.
  - `POST /api/challenges/<id>/join` (`US-4.1`) : inscription rattachant automatiquement l'étudiant à son `campus_id` avec blocage anti-doublon (`409` + contrainte unique SQL `uq_challenge_entry`).
  - `POST /api/challenges/<id>/performances` (`US-4.2`) : soumission JSON ou `multipart/form-data` avec preuve photo optionnelle (`/uploads/proofs/`), validation stricte (`> 0` et plafond anti-triche), verrouillage transactionnel `SELECT ... FOR UPDATE`, cumul individuel & campus + création `Workout` (+20 XP).
  - `GET /api/challenges/<id>/leaderboard` & `GET /api/challenges/leaderboard/global` (`US-4.3`) : podiums Top 3 et classements complets des 4 campus et des participants, tri décroissant fiable, écart au leader et rangs personnels (`my_rank`, `my_campus_rank`).
- **Interface React Défis & Podiums (`frontend/src/components/ChallengesView.jsx`)** :
  - Bandeau Podium Top 3 (`🥇`, `🥈`, `🥉`), bascule **Classement par Défi / Classement Général**, mise en surbrillance de l'école et du rang personnel, barres de progression collectives et tiroir de saisie de performances avec preuve photo.

### Résultats des vérifications
- **`ruff check app tests wsgi.py gunicorn_wsgi.py`** : `All checks passed!`
- **`pytest -v`** : **`30 passed in 23.22s`** (0 warning — 5 Étape 1 + 9 Étape 2 + 8 Étape 3 + 8 nouveaux tests Étape 4 dans `tests/test_step04_challenges.py`).
- **Endpoints HTTP via Nginx (`:8080`)** : `2` défis actifs, `1` défi terminé et classement général des `4` campus opérationnels.
