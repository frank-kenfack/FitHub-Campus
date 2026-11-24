# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Branche active : [`main`](https://github.com/frank-kenfack/FitHub-Campus/tree/main) (`v1.0.0` — synchronisée avec [`develop`](https://github.com/frank-kenfack/FitHub-Campus/tree/develop))  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Topologie Kubernetes (+20 % Bonus) : [docs/RAPPORT_KUBERNETES_STEP08.html](./docs/RAPPORT_KUBERNETES_STEP08.html)  
Rapport qualité & benchmark latence : [docs/RAPPORT_QUALITE_STEP07.html](./docs/RAPPORT_QUALITE_STEP07.html)  
Guide de soutenance jury (15 min) : [docs/DEMO_JURY.md](./docs/DEMO_JURY.md)  
Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)  
Application locale en cours d'exécution : http://localhost:8080

---

## Progression globale : 8 / 8 étapes validées (100 % — MVP + CI/CD + Bonus Kubernetes +20 %)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | [`step-01/socle-docker`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-01/socle-docker) | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | ✅ Fusionnée (`develop`) | 4 conteneurs `healthy` • `pytest` 5/5 |
| **2** | [`step-02/auth-profils-groupes`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-02/auth-profils-groupes) | Auth JWT sécurisée (`bcrypt`), profils + upload avatar persistant, groupes sportifs | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 14/14 |
| **3** | [`step-03/social-fitness`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-03/social-fitness) | Stories workouts (< 24h), partage photos Avant/Après (slider comparatif), likes & commentaires | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 22/22 |
| **4** | [`step-04/defis-classements`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-04/defis-classements) | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 30/30 |
| **5** | [`step-05/fitbuddy-realtime`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-05/fitbuddy-realtime) | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 37/37 • WebSocket live OK |
| **6** | [`step-06/geoloc-gamification`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-06/geoloc-gamification) | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import Google Fit/GPX | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 45/45 |
| **7** | [`step-07/cicd-qualite-docs`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-07/cicd-qualite-docs) | `.gitlab-ci.yml` + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` & architecture | ✅ Fusionnée (`develop`) | `ruff` OK • `pytest` 51/51 • Latence E2E 4–31 ms |
| **8** | [`step-08/kubernetes-bonus`](https://github.com/frank-kenfack/FitHub-Campus/tree/step-08/kubernetes-bonus) | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, HPA, probes, Services, PVC, Ingress WebSocket) + guide démo jury | ✅ Fusionnée (`develop` & `main`) | `ruff` OK • `pytest` **58/58** • `kubectl kustomize` OK |

---

## Détail de l'Étape 8 — `step-08/kubernetes-bonus`

### Livrables implémentés
- **Manifests Kubernetes Complets (`US-8.4` — Bonus `+20 %` dans [`k8s/`](./k8s/))** :
  - [`k8s/00-namespace.yaml`](./k8s/00-namespace.yaml), [`k8s/01-configmap.yaml`](./k8s/01-configmap.yaml), [`k8s/02-secret.yaml`](./k8s/02-secret.yaml) (clés JWT RFC 7518 `>= 36` octets).
  - [`k8s/03-pvc.yaml`](./k8s/03-pvc.yaml) : 2 `PersistentVolumeClaim` (`postgres-data-pvc` `5Gi` & `uploads-data-pvc` `2Gi`).
  - [`k8s/04-postgres.yaml`](./k8s/04-postgres.yaml) & [`k8s/05-redis.yaml`](./k8s/05-redis.yaml) : Deployments et Services `ClusterIP` avec sondes `pg_isready` et `redis-cli ping`.
  - [`k8s/06-backend.yaml`](./k8s/06-backend.yaml) & [`k8s/07-frontend.yaml`](./k8s/07-frontend.yaml) : Deployments haute disponibilité (**2 réplicas**, `RollingUpdate` sans interruption `maxUnavailable: 0`, `runAsNonRoot: true`, probes `/api/health` et `/nginx-health`), Services `ClusterIP` et `HorizontalPodAutoscaler` (`2 → 5` réplicas à `75 %` CPU).
  - [`k8s/08-ingress.yaml`](./k8s/08-ingress.yaml) & [`k8s/kustomization.yaml`](./k8s/kustomization.yaml) : Ingress NGINX routant `/`, `/api`, `/uploads` et `/socket.io` (annotations WebSocket) + compilation Kustomize validée par `kubectl kustomize k8s/` (463 lignes YAML).
  - [`scripts/k8s_deploy.sh`](./scripts/k8s_deploy.sh) : script d'automatisation Kustomize & déploiement cluster.
- **Guide de Soutenance & Démonstration Jury 15 min (`US-9.4`)** :
  - [`docs/DEMO_JURY.md`](./docs/DEMO_JURY.md) : conducteur chronométré minute par minute (5 min Architecture & DevOps, 7 min Parcours Live, 3 min Questions/Réponses Jury).
- **Tests Automatisés Kubernetes (`backend/tests/test_step08_kubernetes_bonus.py`)** :
  - 7 tests vérifiant l'exhaustivité Kustomize, la conformité RFC 7518 des secrets K8s, les 2 PVC, la haute disponibilité (`replicas >= 2`, `RollingUpdate`, `runAsNonRoot`), les probes/resources sur chaque workload, le HPA et le routage WebSocket de l'Ingress.
