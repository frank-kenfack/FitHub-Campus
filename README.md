# FITHUB CAMPUS

FitHub Campus est un réseau social sportif destiné aux étudiants. L'application réunit dans une interface unique la gestion de clubs par établissement, le partage de séances d'entraînement, les défis sportifs inter-campus, la mise en relation de partenaires en temps réel, la géolocalisation de lieux et d'événements, ainsi que la progression par points d'expérience et badges.


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


## ÉTAPES DE CONFIGURATION EFFECTUÉES

### Paramétrage des variables d'environnement et de la sécurité

La configuration locale et conteneurisée repose sur `.env.example`, qui définit la chaîne de connexion `DATABASE_URL` vers PostgreSQL 16 (`postgresql://fithub_user:fithub_dev_pwd@db:5432/fithub`), l'adresse du courtier `REDIS_URL` (`redis://redis:6379/0`), les clés `SECRET_KEY` et `JWT_SECRET_KEY` dimensionnées pour HMAC-SHA256 selon la norme RFC 7518 (32 octets minimum), le dossier de stockage `UPLOAD_FOLDER=/app/uploads` et les ports `FRONTEND_PORT=8080` et `BACKEND_PORT=5000`.


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
└── docs/                              Architecture technique 
```
