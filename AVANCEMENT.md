# FitHub Campus — Journal d'Avancement & Visualisation

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus  
Tableau de bord visuel interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)  
Backlog MVP complet : [FitHub_Campus_Backlog_MVP.pdf](./FitHub_Campus_Backlog_MVP.pdf)

---

## Progression globale : 0 / 8 étapes validées (Initialisation en cours)

| Étape | Branche Git | Périmètre principal | Statut | Validation / Tests |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `step-01/socle-docker` | Socle Git, MCD/Migrations PostgreSQL, Stack Docker 4 conteneurs, `/api/health`, Squelette UI mobile-first | 🔄 En cours | En attente |
| **2** | `step-02/auth-profils-groupes` | Auth JWT sécurisée (bcrypt), profils + upload avatar persistant, groupes sportifs | ⏳ À faire | — |
| **3** | `step-03/social-fitness` | Stories workouts, partage photos Avant/Après (slider comparatif), likes & commentaires | ⏳ À faire | — |
| **4** | `step-04/defis-classements` | Création/participation défis inter-campus, soumission performances, leaderboards campus & individuels | ⏳ À faire | — |
| **5** | `step-05/fitbuddy-realtime` | Matching Fit-Buddy, encouragements temps réel Flask-SocketIO + Redis, streak partagé | ⏳ À faire | — |
| **6** | `step-06/geoloc-gamification` | Carte Leaflet/OSM salles & événements + RSVP + filtres Haversine + badges automatiques + import JSON/GPX | ⏳ À faire | — |
| **7** | `step-07/cicd-qualite-docs` | `.gitlab-ci.yml` complet + `.github/workflows/ci.yml`, scripts Bash/Ansible, recette E2E & perfs `< 300 ms`, `README.md` final | ⏳ À faire | — |
| **8** | `step-08/kubernetes-bonus` | Manifests `k8s/` complets (+20 % bonus : Deployments ≥ 2 réplicas, probes, Services, PV/PVC, Ingress WebSocket) + guide démo jury | ⏳ À faire | — |

---

## Règle de workflow Git
1. Chaque étape est développée sur sa branche dédiée `step-XX/...` créée depuis `develop`.
2. Une batterie de tests automatisés et manuels est exécutée et consignée avant tout passage à l'étape suivante.
3. Après validation visuelle par l'utilisateur (`docs/SUIVI_ETAPES.html` + aperçu applicatif), la branche est fusionnée dans `develop` avant d'ouvrir la branche suivante.
