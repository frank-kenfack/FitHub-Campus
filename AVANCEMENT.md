# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`step-07/cicd-qualite-docs`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-07/cicd-qualite-docs)  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Rapport qualité & benchmark latence : [docs/RAPPORT_QUALITE_STEP07.html](./docs/RAPPORT_QUALITE_STEP07.html)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 7 / 8 étapes validées (87,5 % — Industrialisation CI/CD & Documentation Complètes)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `pytest` 5/5 |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 14/14 |
| **3** | [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness) | Stories workouts (< 24h), partage photos Avant/Après (slider comparatif), likes & commentaires | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 22/22 |
| **4** | [`step-04/defis-classements`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-04/defis-classements) | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 30/30 |
| **5** | [`step-05/fitbuddy-realtime`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-05/fitbuddy-realtime) | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 37/37 • WebSocket live OK |
| **6** | [`step-06/geoloc-gamification`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-06/geoloc-gamification) | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import Google Fit/GPX | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 45/45 |
| **7** | [`step-07/cicd-qualite-docs`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-07/cicd-qualite-docs) | `.gitlab-ci.yml` + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` & architecture | ✅ Validée (attente revue) | `ruff` OK • `pytest` **51/51** • Latence E2E **4–31 ms** |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Détail de l'Étape 7 — `step-07/cicd-qualite-docs`

### Livrables implémentés
- **Pipelines CI/CD complets (`US-8.2`)** :
  - [`.gitlab-ci.yml`](./.gitlab-ci.yml) : 4 stages séquentiels (`lint`, `test`, `build`, `deploy`), services PostgreSQL 16 + Redis 7, rapport JUnit XML, publication d'images Docker multi-stages et déploiement Ansible vers `staging` / `production`.
  - [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) : workflow GitHub Actions opérationnel en 3 jobs (`lint-and-frontend`, `pytest-integration`, `docker-compose-smoke`).
- **Scripts d'Automatisation & Playbook Ansible (`US-8.3`)** :
  - [`scripts/deploy.sh`](./scripts/deploy.sh), [`scripts/run_tests.sh`](./scripts/run_tests.sh), [`scripts/smoke_test.sh`](./scripts/smoke_test.sh) et [`.gitattributes`](./.gitattributes) (normalisation LF Unix garantie).
  - [`infra/ansible/deploy.yml`](./infra/ansible/deploy.yml) et [`infra/ansible/inventory.ini.example`](./infra/ansible/inventory.ini.example) : déploiement reproductible sur VM Linux et contrôle de santé automatique.
- **Recette End-to-End, Sécurité & Performance `< 300 ms` (`US-9.1`, `US-9.2` — `backend/tests/test_step07_quality_perf.py`)** :
  - Parcours E2E traversant les 6 modules jusqu'au déblocage de **5/5 badges**, benchmark de latence `< 300 ms` (mesurée entre **4 ms et 31 ms** derrière Nginx `:8080`), résistance aux injections SQL, rejet des valeurs `NaN`/`Inf` et réponses d'erreur `404`/`405` structurées en JSON.
- **Documentation Technique Finale (`US-9.3`)** :
  - [`README.md`](./README.md) enrichi avec schémas Mermaid, table complète des API, guide de démarrage rapide et mesures de sécurité.
  - [`docs/ARCHITECTURE_TECHNIQUE.md`](./docs/ARCHITECTURE_TECHNIQUE.md) détaillant le MCD 16 tables, le fan-out temps réel Redis/Socket.IO et la chaîne DevOps.
