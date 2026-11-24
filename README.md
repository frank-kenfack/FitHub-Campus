# FITHUB CAMPUS

FitHub Campus est un réseau social sportif destiné aux étudiants. L'application réunit dans une interface unique la gestion de clubs par établissement, le partage de séances d'entraînement, les défis sportifs inter-campus, la mise en relation de partenaires en temps réel, la géolocalisation de lieux et d'événements, ainsi que la progression par points d'expérience et badges.

Le dépôt hébergé sur GitHub (`https://github.com/frank-kenfack/FitHub-Campus`) est livré en version `v1.0.0` sur les branches `main` et `develop`, à l'issue de huit étapes de développement intégrées selon un flux Git-Flow complet.

## TRAVAIL RÉALISÉ DE FAÇON DÉTAILLÉE

### Développement incrémental en huit étapes Git-Flow

Chaque fonctionnalité a été conçue sur une branche dédiée, contrôlée par des tests automatisés sur PostgreSQL 16 et Redis 7, puis fusionnée dans `develop` avant la sortie finale sur `main`.

1. **Étape 1 (`step-01/socle-docker`) : socle technique, schéma relationnel et pile Docker.** Mise en place de l'arborescence projet, de la migration Alembic initiale (`backend/migrations/versions/b7ed6f971fa6_initial_schema.py`) créant 16 tables liées par clés étrangères, du chargement initial idempotent (`backend/app/seed.py`), de l'orchestration Docker Compose à quatre conteneurs et de la sonde `GET /api/health` (5 tests validés).
2. **Étape 2 (`step-02/auth-profils-groupes`) : authentification JWT, profils et clubs sportifs.** Implémentation de l'inscription et de la connexion avec hachage `bcrypt` et jetons `Flask-JWT-Extended`, édition du profil étudiant, téléversement et redimensionnement d'avatar via `Pillow`, création de clubs par campus et adhésion protégée par la contrainte d'unicité `uq_group_member` (14 tests validés).
3. **Étape 3 (`step-03/social-fitness`) : fil social, séances éphémères et comparatifs.** Ajout de publications de séances avec durée d'expiration de 24 heures, double téléversement photo avant et après accompagné d'un curseur visuel, restriction de visibilité aux membres d'un club, mentions j'aime idempotentes (`uq_story_like`) et gestion des commentaires (22 tests validés).
4. **Étape 4 (`step-04/defis-classements`) : défis inter-campus et classements en direct.** Création de défis collectifs, soumission de performances chiffrées avec preuve photo optionnelle, cumul automatique des scores individuels et par campus sous contrainte `uq_challenge_entry`, et affichage des classements individuels et généraux (30 tests validés).
5. **Étape 5 (`step-05/fitbuddy-realtime`) : partenaires d'entraînement et messagerie temps réel.** Développement du calcul de compatibilité entre étudiants dans `backend/app/services/buddy_matching.py` selon le campus, les disciplines et le niveau, gestion des invitations et acceptations, messagerie instantanée d'encouragements via `Flask-SocketIO` et `Redis 7`, et calcul des séries de jours consécutifs partagés en binôme (37 tests validés).
6. **Étape 6 (`step-06/geoloc-gamification`) : carte Leaflet, événements, badges et import GPX.** Intégration d'une carte interactive `Leaflet`, filtrage géographique par rayon via la formule de Haversine (`6371,0088 km`), inscriptions aux événements protégées contre les accès concurrents par verrou `SELECT ... FOR UPDATE` et contrainte `uq_event_rsvp`, attribution automatique de cinq badges (`backend/app/services/badge_progression.py`), paliers de récompenses et synchronisation de séances JSON Google Fit ou traces XML `.gpx` protégées contre les entités externes XML (anti-XXE) (45 tests validés).
7. **Étape 7 (`step-07/cicd-qualite-docs`) : intégration continue, déploiement Ansible et recette.** Mise en place des chaînes GitLab CI (`.gitlab-ci.yml`) et GitHub Actions (`.github/workflows/ci.yml`), du playbook Ansible (`infra/ansible/deploy.yml`), des scripts d'exploitation (`scripts/deploy.sh`, `scripts/run_tests.sh`, `scripts/smoke_test.sh`), de tests de sécurité (résistance aux injections SQL, rejet des valeurs `NaN`/`Inf`, contrôle des en-têtes CORS) et d'une recette de bout en bout validant des latences sous `300 ms` (51 tests validés).
8. **Étape 8 (`step-08/kubernetes-bonus`) : orchestration Kubernetes et préparation de soutenance.** Écriture et validation Kustomize de 14 ressources sous `k8s/`, haute disponibilité avec mise à l'échelle horizontale automatique, vérification complète de la pile et rédaction du conducteur de soutenance (`docs/DEMO_JURY.md`) et des rapports visuels (58 tests validés).

### Refonte de l'interface et structuration du code métier

Une reprise complète de l'interface React (`frontend/src/`) a remplacé les vues de démonstration techniques par une navigation en français répartie sur huit onglets : « Accueil », « Fil social », « Défis », « Partenaires », « Carte et lieux », « Clubs », « Récompenses » et « Mon espace ». La présentation utilise la police Times New Roman (`14px` pour le texte courant, `12px` pour les mentions secondaires) avec des titres principaux en majuscules taille `16`.

Côté serveur, l'ancien répertoire générique `utils` a été remplacé par `backend/app/services/` comprenant quatre modules spécialisés : `buddy_matching.py`, `badge_progression.py`, `media_storage.py` et `domain_serializers.py`. Les identifiants de variables et les commentaires ont été alignés sur le vocabulaire métier en ne conservant que les justifications techniques utiles.

## ÉTAPES DE CONFIGURATION EFFECTUÉES

### Paramétrage des variables d'environnement et de la sécurité

La configuration locale et conteneurisée repose sur `.env.example`, qui définit la chaîne de connexion `DATABASE_URL` vers PostgreSQL 16 (`postgresql://fithub_user:fithub_dev_pwd@db:5432/fithub`), l'adresse du courtier `REDIS_URL` (`redis://redis:6379/0`), les clés `SECRET_KEY` et `JWT_SECRET_KEY` dimensionnées pour HMAC-SHA256 selon la norme RFC 7518 (32 octets minimum), le dossier de stockage `UPLOAD_FOLDER=/app/uploads` et les ports `FRONTEND_PORT=8080` et `BACKEND_PORT=5000`.

### Construction Docker multi-étapes et isolation réseau

Le fichier `docker-compose.yml` isole quatre services au sein du réseau pont `fithub_net`, persiste les données dans les volumes nommés `postgres_data` et `uploads_data`, monte `k8s/` en lecture seule sur le serveur et coordonne le démarrage grâce aux sondes de santé (`pg_isready`, `redis-cli ping`, `/api/health` et `/nginx-health`).

Les images ont été configurées en deux étapes pour réduire leur empreinte et exécuter chaque processus sans privilèges administrateur :

- **Serveur Flask et Socket.IO (`backend/Dockerfile`, `backend/entrypoint.sh`)** : compilation des bibliothèques C et Python sous `python:3.12-slim`, copie dans une image finale allégée dotée de `libpq5`, exécution sous l'utilisateur non privilégié `appuser`, normalisation des fins de ligne de `entrypoint.sh`, exécution automatique de `flask --app wsgi:app db upgrade` puis de `python -m app.seed`, et démarrage de `gunicorn` avec le worker `eventlet` sur le port `5000`.
- **Interface React et proxy inverse (`frontend/Dockerfile`, `frontend/nginx.conf`)** : compilation du bundle Vite sous `node:20-alpine`, puis service des fichiers statiques via `nginxinc/nginx-unprivileged:1.27-alpine` sur le port `8080`. Nginx transmet `/api/` et `/uploads/` vers `backend:5000`, active la mise à niveau HTTP 1.1 `Upgrade: websocket` sur `/socket.io/` et expose `/nginx-health`.

### Automatisation CI/CD, déploiement Ansible et manifests Kubernetes

La validation continue s'appuie sur `.github/workflows/ci.yml` (analyse statique `ruff`, build Vite, contrôle `kubectl kustomize k8s/`, tests Pytest adossés à PostgreSQL 16 et Redis 7, puis test de fumée sur les quatre conteneurs) et sur `.gitlab-ci.yml` en quatre stades (`lint`, `test`, `build`, `deploy`). Le playbook `infra/ansible/deploy.yml` installe Docker et Docker Compose v2 sur les hôtes cibles, synchronise le dépôt dans `/opt/fithub-campus`, initialise `.env` en mode `0600`, lance la pile avec `--wait` et vérifie la réponse JSON de `/api/health`.

La cible Kubernetes (`k8s/kustomization.yaml`) rassemble 14 ressources réparties de `00-namespace.yaml` à `08-ingress.yaml` dans l'espace de noms `fithub-campus` : un `ConfigMap`, quatre secrets conformes RFC 7518, deux volumes persistants (`5 Gi` pour PostgreSQL et `2 Gi` pour les médias), un déploiement backend répliqué de 2 à 5 pods selon la charge CPU (`75 %` via `HorizontalPodAutoscaler`), un déploiement frontend à 2 réplicas, des sondes `liveness` et `readiness` ainsi qu'un `Ingress` NGINX gérant HTTP et WebSocket.

## CE QU'IL EN RESSORT À LA FIN

L'application livrée fonctionne de bout en bout dès le premier démarrage sur `http://localhost:8080`, avec une base pré-remplie contenant quatre campus (Lyon Gerland, Paris Nation, Bordeaux Chartrons, Lille EuraTechnologies), quatre comptes étudiants actifs, des clubs sportifs, des publications illustrées générées par `Pillow`, des défis collectifs, des lieux géolocalisés et cinq badges de progression.

Sur le plan de la qualité et des vérifications techniques, l'état final du dépôt présente les résultats observés suivants :

- **Suite de tests et analyse statique** : les 58 tests `pytest` répartis sur les huit étapes (`backend/tests/test_step01_socle.py` à `test_step08_kubernetes_bonus.py`) passent sans échec ni avertissement critique, et `ruff check app tests wsgi.py gunicorn_wsgi.py` ne signale aucune erreur.
- **Performances mesurées** : les appels API critiques relevés lors de la recette (`docs/RAPPORT_QUALITE_STEP07.html`) répondent entre `4 ms` et `31 ms`, sous le seuil maximal fixé à `300 ms`.
- **Orchestration et documentation** : la compilation `kubectl kustomize k8s/` génère `463` lignes YAML valides pour les 14 ressources du cluster, et l'ensemble documentaire est complet (`FitHub_Campus_Backlog_MVP.pdf`, `AVANCEMENT.md`, `CAPTURES_ETAPES.md`, `docs/ARCHITECTURE_TECHNIQUE.md`, `docs/DEMO_JURY.md` et les tableaux de bord HTML sous `docs/`).

## CLONER ET INSTALLER LE DÉPÔT SUR UN NOUVEAU POSTE DE TRAVAIL

### Prérequis sur le nouveau poste

Le poste de travail doit disposer de `Git` et de `Docker` avec `Docker Compose v2` (Docker Desktop avec moteur Linux sous Windows ou macOS, ou Docker Engine sous Linux). Les ports TCP `8080` et `5000` doivent être libres localement.

### Étape 1 : cloner le dépôt Git

Récupérez l'intégralité du projet et placez-vous dans le répertoire racine :

```bash
git clone https://github.com/frank-kenfack/FitHub-Campus.git
cd FitHub-Campus
```

Si vous souhaitez travailler sur la branche d'intégration plutôt que sur `main`, basculez ensuite avec `git checkout develop`.

### Étape 2 : préparer le fichier d'environnement

Copiez le modèle `.env.example` vers `.env` à la racine du projet :

```bash
# Linux / macOS / Git Bash
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

Les valeurs par défaut permettent un lancement immédiat en local. En environnement partagé ou si le port `8080` est déjà occupé, modifiez `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET_KEY` (au moins 32 caractères) et `FRONTEND_PORT` dans `.env`.

### Étape 3 : construire et démarrer les quatre conteneurs

Lancez la construction des images et le démarrage complet avec attente des sondes de santé :

```bash
docker compose up --build -d --wait
```

Lors du premier démarrage, Docker télécharge `postgres:16-alpine` et `redis:7-alpine`, compile le serveur Python et le bundle frontend, applique automatiquement les migrations Alembic dans PostgreSQL et exécute `python -m app.seed` pour charger les données de démonstration. Vérifiez que les quatre conteneurs affichent l'état `healthy` :

```bash
docker compose ps
```

### Étape 4 : accéder à l'application et utiliser les comptes de démonstration

Ouvrez `http://localhost:8080` dans votre navigateur. La sonde serveur est également consultable à l'adresse `http://localhost:8080/api/health`. Quatre comptes étudiants prêts à l'emploi sont créés par `app/seed.py` avec le mot de passe commun `Password123!` (accessibles en un clic depuis les boutons de connexion rapide de l'accueil) :

| Identifiant | Adresse e-mail | Campus | Mot de passe |
| :--- | :--- | :--- | :--- |
| `InaFit_Lyon` | `ina.lyon@fithub.fr` | Campus Lyon Gerland | `Password123!` |
| `LucasBarz_Paris` | `lucas.paris@fithub.fr` | Campus Paris Nation | `Password123!` |
| `SarahRun_Bdx` | `sarah.bordeaux@fithub.fr` | Campus Bordeaux Chartrons | `Password123!` |
| `MehdiLift_Lille` | `mehdi.lille@fithub.fr` | Campus Lille EuraTechnologies | `Password123!` |

### Étape 5 : exécuter les vérifications et administrer la pile

Toutes les commandes suivantes s'exécutent depuis la racine du dépôt cloné une fois les conteneurs démarrés :

```bash
# Analyse statique Python (Ruff)
docker compose exec -T backend ruff check app tests wsgi.py gunicorn_wsgi.py

# Suite complète des 58 tests automatisés (Pytest)
docker compose exec -T backend pytest -v

# Contrôle des manifests Kubernetes (si kubectl est installé)
kubectl kustomize k8s/

# Suivi des journaux en direct
docker compose logs -f

# Arrêt des conteneurs en conservant la base et les médias
docker compose down

# Réinitialisation complète (suppression des conteneurs et des volumes)
docker compose down -v
```

Sous Linux ou macOS, le script `./scripts/run_tests.sh` enchaîne également `ruff`, `pytest` et les tests de fumée HTTP via `./scripts/smoke_test.sh`.

## ORGANISATION DES DOSSIERS DU DÉPÔT

```text
FitHub-Campus/
├── .github/workflows/ci.yml           Pipeline GitHub Actions (lint, build, Kustomize, Pytest, Docker)
├── .gitlab-ci.yml                     Pipeline GitLab CI (lint, test, build, deploy)
├── .env.example                       Variables d'environnement de référence
├── docker-compose.yml                 Orchestration des 4 services (db, redis, backend, frontend)
├── backend/
│   ├── Dockerfile                     Image multi-étapes non-root Python 3.12 + libpq5
│   ├── entrypoint.sh                  Migrations Alembic, seed idempotent et Gunicorn eventlet
│   ├── migrations/                    Historique Alembic (16 tables PostgreSQL)
│   ├── app/
│   │   ├── models.py                  Modèles SQLAlchemy et contraintes d'unicité
│   │   ├── routes/                    Points d'entrée REST par domaine fonctionnel
│   │   ├── services/                  Logique métier (matching, badges, médias, sérialisation)
│   │   ├── sockets.py                 Gestion WebSocket Socket.IO avec file Redis
│   │   └── seed.py                    Jeu de données de démonstration et génération visuelle Pillow
│   └── tests/                         58 tests automatisés couvrant les étapes 1 à 8
├── frontend/
│   ├── Dockerfile                     Build Node 20 puis distribution Nginx non privilégiée
│   ├── nginx.conf                     Proxy inverse /api/, /uploads/ et Upgrade WebSocket /socket.io/
│   └── src/                           Application React, Leaflet et client Socket.IO
├── k8s/                               14 manifests Kubernetes Kustomize (00-namespace à 08-ingress)
├── infra/ansible/                     Playbook et inventaire de déploiement Ansible
├── scripts/                           Scripts Bash d'exploitation, de tests et de déploiement k8s
├── docs/                              Architecture technique, guide jury, rapports HTML et captures
├── AVANCEMENT.md                      Journal récapitulatif des 8 étapes
├── CAPTURES_ETAPES.md                 Suivi visuel par étape
└── FitHub_Campus_Backlog_MVP.pdf      Cahier des charges et backlog produit
```
