# FITHUB CAMPUS : JOURNAL D'AVANCEMENT

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus

Branche principale : [`main`](https://github.com/frank-kenfack/FitHub-Campus/tree/main) (`v1.0.0`, synchronisée avec [`develop`](https://github.com/frank-kenfack/FitHub-Campus/tree/develop))

Tableau de bord visuel : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)

Rapport qualité et latence : [docs/RAPPORT_QUALITE_STEP07.html](./docs/RAPPORT_QUALITE_STEP07.html)

Topologie Kubernetes : [docs/RAPPORT_KUBERNETES_STEP08.html](./docs/RAPPORT_KUBERNETES_STEP08.html)

Guide de soutenance jury : [docs/DEMO_JURY.md](./docs/DEMO_JURY.md)

Album des captures par étape : [CAPTURES_ETAPES.md](./CAPTURES_ETAPES.md)

Application locale : http://localhost:8080

## PROGRESSION GLOBALE : 8 SUR 8 ÉTAPES VALIDÉES (100 %)

| Étape | Branche Git | Périmètre principal | Statut | Tests et vérifications |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `step-01/socle-docker` | Socle Git, migrations PostgreSQL, pile Docker 4 conteneurs, santé API, interface mobile | Fusionnée (`develop` et `main`) | 4 conteneurs prêts, `pytest` 5/5 |
| **2** | `step-02/auth-profils-groupes` | Authentification JWT (`bcrypt`), profils avec avatar, clubs sportifs | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 14/14 |
| **3** | `step-03/social-fitness` | Stories de séances, comparatifs avant et après, mentions j'aime et commentaires | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 22/22 |
| **4** | `step-04/defis-classements` | Défis intercampus, scores, preuves photo et classements | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 30/30 |
| **5** | `step-05/fitbuddy-realtime` | Recherche de partenaires, encouragements WebSocket et Redis, séries de jours | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 37/37 |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet, filtrage Haversine, inscriptions avec capacité, badges et import GPX | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 45/45 |
| **7** | `step-07/cicd-qualite-docs` | Pipelines GitLab CI et GitHub Actions, scripts Bash, Ansible, recette E2E | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 51/51, latence 4 à 31 ms |
| **8** | `step-08/kubernetes-bonus` | Manifests Kubernetes (`k8s/`), haute disponibilité, guide de soutenance | Fusionnée (`develop` et `main`) | `ruff` valide, `pytest` 58/58, `kubectl kustomize` valide |

## DÉTAIL DE LA RÉALISATION FINALE

Le dépôt rassemble l'application complète avec son interface en français réajustée pour les étudiants, les services métier séparés sous `backend/app/services/`, l'orchestration Kubernetes dans `k8s/` et la chaîne de tests automatisés exécutée sur PostgreSQL 16 et Redis 7.
