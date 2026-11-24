# FitHub Campus — Guide de Soutenance & Démonstration Jury (15 Minutes)

Ce document structure la soutenance finale devant le jury d'évaluation B3 (**15 minutes** : 5 min Architecture & DevOps, 7 min Démonstration Live Multi-Modules, 3 min Questions/Réponses Techniques).

---

## 1. Check-list Avant Passage (T - 5 min)

1. Vérifier que les 4 conteneurs sont actifs et `healthy` :
   ```bash
   ./scripts/deploy.sh
   ```
2. Ouvrir deux fenêtres navigateur côte à côte sur `http://localhost:8080` :
   - **Fenêtre A (Principale)** : connectée en 1 clic sur **`InaFit_Lyon`** (Campus Lyon Gerland).
   - **Fenêtre B (Navigation privée / second profil)** : connectée en 1 clic sur **`SarahRun_Bdx`** (Campus Bordeaux Chartrons) sur l'onglet **Buddy** pour démontrer le WebSocket temps réel sans rechargement.
3. Garder ouverts dans des onglets dédiés :
   - Le tableau de bord visuel : [docs/SUIVI_ETAPES.html](./SUIVI_ETAPES.html) (**100 % — 8/8 étapes — 58/58 Pytest**)
   - L'architecture Kubernetes (+20 % Bonus) : [docs/RAPPORT_KUBERNETES_STEP08.html](./RAPPORT_KUBERNETES_STEP08.html)
   - Le rapport de performance `< 300 ms` : [docs/RAPPORT_QUALITE_STEP07.html](./RAPPORT_QUALITE_STEP07.html)

---

## 2. Minuteur & Scénario de Présentation (15 min)

### Séquence 1 — Vision Produit, Architecture Cloud-Native & DevOps (00:00 → 05:00)

- **00:00 – 01:00 | Pitch & Découpage Agile** :
  - Présentation de **FitHub Campus** (Option B — Réseau Social Fitness Étudiant) : lutter contre la sédentarité étudiante par l'émulation inter-campus.
  - Montrer le backlog découpé ([FitHub_Campus_Backlog_MVP.pdf](../FitHub_Campus_Backlog_MVP.pdf) : 9 Epics, 30 User Stories) et la méthodologie **Gitflow en 8 branches** (`step-01` → `step-08` fusionnées dans `develop` puis `main` uniquement après validation par les tests).
- **01:00 – 03:00 | Architecture 4 Conteneurs & Sécurité** :
  - Présenter `docker-compose.yml` :
    - `fithub-frontend` (`nginxinc/nginx-unprivileged:1.27-alpine`, UID 101, reverse proxy HTTP + WebSocket `/socket.io`),
    - `fithub-backend` (Python 3.12, Flask 3, Gunicorn/Eventlet, utilisateur non-root `appuser`),
    - `fithub-db` (PostgreSQL 16 Alpine, 16 tables migrées via Alembic, volume `postgres_data`),
    - `fithub-redis` (Redis 7 Alpine, broker pub/sub Socket.IO).
- **03:00 – 05:00 | Chaîne CI/CD, Ansible & Bonus Kubernetes (+20 %)** :
  - Montrer `.gitlab-ci.yml` (4 stages `lint`, `test`, `build`, `deploy`), `.github/workflows/ci.yml` (3 jobs cloud) et `infra/ansible/deploy.yml`.
  - Présenter la pile Kubernetes (`k8s/00-namespace.yaml` à `08-ingress.yaml` + `kustomization.yaml`) :
    - Haute disponibilité (`replicas: 2` sur `fithub-backend` et `fithub-frontend`, `RollingUpdate` `maxUnavailable: 0`),
    - Auto-scaling horizontal (`HorizontalPodAutoscaler` `2` → `5` pods à `75 %` CPU),
    - Persistance `postgres-data-pvc` (`5Gi`) & `uploads-data-pvc` (`2Gi`),
    - `Ingress` NGINX gérant l'Upgrade WebSocket `/socket.io` pendant que Redis synchronise les événements entre les 2 pods backend.

---

### Séquence 2 — Démonstration Live de l'Application (05:00 → 12:00)

1. **05:00 – 06:00 | Accueil, Auth JWT & Groupes Sportifs (`EP-01`, `EP-02`)** :
   - Sur **Accueil**, montrer l'état temps réel des 4 conteneurs (`Opérationnel`, `Connectés`).
   - Sur **Profil**, montrer les statistiques d'`InaFit_Lyon`, l'upload d'avatar persistant (`/uploads/avatars/`) et sur **Groupes**, filtrer par campus/sport et rejoindre un club.
2. **06:00 – 07:30 | Social Fitness : Stories 24h & Slider Avant/Après (`EP-03`)** :
   - Sur **Social**, cliquer sur une bulle du carrousel **Stories `< 24h`**.
   - Manipuler le **curseur coulissant Avant/Après** (`clip-path` interactif + bascule *Côte à côte*) sur la publication HYROX de Sarah, ajouter un like idempotent et un commentaire.
3. **07:30 – 09:00 | Défis Inter-Campus & Podiums (`EP-04`)** :
   - Sur **Défis**, afficher le **Podium Inter-Campus Top 3** (*Campus Lyon Gerland* vs *Lille*, *Bordeaux*, *Paris*).
   - Ouvrir **« + Performance »**, saisir `+5 km` avec preuve photo → observer la mise à jour transactionnelle immédiate de la barre de progression et du classement général XP.
4. **09:00 – 10:30 | Fit-Buddy & WebSocket Temps Réel 2 Navigateurs (`EP-05`)** :
   - Afficher **Fenêtre A (`InaFit_Lyon`)** et **Fenêtre B (`SarahRun_Bdx`)** côte à côte sur l'onglet **Buddy** (`🟢 Live WebSocket Connecté`, `🔥 4 j streak`).
   - Depuis la **Fenêtre B**, cliquer sur le boost 1-clic `🔥 Go training !` → montrer l'apparition **instantanée sans rechargement** du toast vert et de la bulle dans la **Fenêtre A**, ainsi que le score d'affinité (`%`) dans l'explorateur de binômes.
5. **10:30 – 12:00 | Carte Leaflet Haversine, RSVP & Gamification Google Fit / GPX (`EP-06`, `EP-07`)** :
   - Sur **Carte**, cliquer sur **Lyon** + rayon **Moins de 5 km** → montrer le cercle Haversine sur la carte **Leaflet / OpenStreetMap**, cliquer pour créer un événement ou confirmer sa présence (**RSVP** avec plafond `max_participants`).
   - Sur **Badges**, lancer en 1 clic **« Synchroniser depuis Google Fit (+30 XP) »** (ou importer une trace `.gpx`) → montrer le crédit automatique sur le défi inter-campus actif, l'avancement du palier (*Athlète Or* / *Légende Campus*) et la vitrine des **5/5 badges**.

---

### Séquence 3 — Réponses aux Questions Fréquentes du Jury (12:00 → 15:00)

| Question potentielle du jury | Réponse technique précise à apporter |
| :--- | :--- |
| **« Comment fonctionnent les WebSockets si Kubernetes déploie 2 réplicas du backend ? »** | Flask-SocketIO est connecté au broker **Redis 7** (`message_queue=REDIS_URL`). Chaque étudiant rejoint sa room logique `user_<id>`. Quand le Pod Backend 1 émet un encouragement, Redis diffuse le message via Pub/Sub au Pod Backend 2 qui le pousse instantanément au client connecté. |
| **« Comment évitez-vous qu'un événement ou un défi dépasse sa capacité ou subisse des doublons en cas de clics simultanés ? »** | Double verrouillage : contraintes d'unicité PostgreSQL (`uq_event_rsvp`, `uq_challenge_entry`, `uq_user_badge`) + verrouillage pessimiste transactionnel SQLAlchemy `with_for_update()` (`SELECT ... FOR UPDATE`) avant vérification de `max_participants` ou addition de score. |
| **« Comment est sécurisé l'upload de photos et de fichiers GPX ? »** | Pour les images : vérification binaire réelle et ré-encodage par **Pillow** (rejette tout script déguisé en `.png`), nommage `UUID4` hors du code source. Pour le GPX : rejet préventif de toute déclaration `<!DOCTYPE` ou `<!ENTITY` (protection anti-XXE) et validation des bornes géographiques. |
| **« Comment garantissez-vous le temps de réponse `< 300 ms` ? »** | Conteneur Nginx statique en frontal, pool de connexions SQLAlchemy vers PostgreSQL 16 indexé, worker asynchrone Eventlet et tests de performance automatisés (`test_critical_api_endpoints_latency_under_300ms` + `scripts/smoke_test.sh` mesurant **4 à 31 ms**). |
