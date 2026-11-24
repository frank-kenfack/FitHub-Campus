# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-06/geoloc-gamification`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-06/geoloc-gamification)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 6 / 8 étapes validées (75 % — MVP Fonctionnel Complet)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `pytest` 5/5 |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 14/14 |
| **3** | [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness) | Stories workouts (< 24h), partage photos Avant/Après (slider comparatif), likes & commentaires | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 22/22 |
| **4** | [`step-04/defis-classements`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-04/defis-classements) | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 30/30 |
| **5** | [`step-05/fitbuddy-realtime`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-05/fitbuddy-realtime) | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 37/37 • WebSocket live OK |
| **6** | [`step-06/geoloc-gamification`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-06/geoloc-gamification) | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import Google Fit/GPX | ✅ Validée (attente revue) | `ruff` OK • `pytest` **45/45** (0 warning) |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 6 — `step-06/geoloc-gamification`

### Livrables implémentés
- **Géolocalisation, Salles, Spots & Événements (`EP-06` : `US-6.1`, `US-6.2`, `US-6.3` — `backend/app/routes/places.py`)** :
  - `GET /api/places` : calcul orthodromique exact **Haversine** (`haversine_km`), filtrage combinable par `kind` (`gym` / `spot` / `event`), `sport`, `campus_id` et `radius_km`, avec repli automatique sur les coordonnées GPS du campus si le navigateur ne fournit pas `lat`/`lon`.
  - `POST /api/places/events` : création d'événements géolocalisés avec sélection directe sur la carte, auto-inscription de l'organisateur (`+20 XP`) et déblocage immédiat du badge *Participant Événement*.
  - `POST /api/places/<id>/rsvp` & `DELETE /api/places/<id>` : gestion transactionnelle (`with_for_update()`) des inscriptions avec blocage `409 Conflict` dès l'atteinte de `max_participants` et protection des salles partenaires contre la suppression.
- **Moteur de Gamification, Paliers XP & Connecteur Externe (`EP-07` : `US-7.1`, `US-7.2`, `US-7.3` — `backend/app/utils/gamification.py`, `backend/app/routes/gamification.py`)** :
  - Attribution automatique **sans doublon** des 5 badges (`Premier Workout`, `5 Séances`, `Fit-Buddy Solidaire`, `Top Campus`, `Participant Événement`) branchée sur les stories, performances défis, encouragements Fit-Buddy, RSVP événements et imports.
  - Échelle de progression en 4 paliers (*Athlète Bronze*, *Athlète Argent*, *Athlète Or*, *Légende Campus*) avec jauge de progression et catalogue de récompenses virtuelles.
  - `POST /api/gamification/import-activity` : synchronisation de sessions **Google Fit REST JSON** et import de traces GPS **`.gpx` / `.json`** (calcul de distance Haversine sur `<trkpt>`, protection anti-XXE), créditant simultanément le journal de séances, l'XP et le défi inter-campus actif correspondant.
- **Interfaces React (`frontend/src/components/MapEventsView.jsx`, `frontend/src/components/GamificationView.jsx`)** :
  - Carte interactive **Leaflet 1.9 + OpenStreetMap** avec marqueurs personnalisés (`GYM`, `SPOT`, `EVENT`, `GPS`), tracé visuel du rayon Haversine, popups détaillées et raccourcis campus.
  - Tableau de bord des paliers XP, vitrine des 5 badges et connecteur 1-clic Google Fit + import/téléchargement `.gpx`.

### Résultats des vérifications
- **`ruff check app tests wsgi.py gunicorn_wsgi.py`** : `All checks passed!`
- **`pytest -v`** : **`45 passed in 31.80s`** (0 warning — Étapes 1 à 6 complètes).
