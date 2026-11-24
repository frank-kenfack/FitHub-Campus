# FITHUB CAMPUS : ALBUM DES CAPTURES D'ÉCRAN PAR ÉTAPE

Ce document rassemble les captures d'écran de validation pour chacune des huit étapes du projet FitHub Campus.

Dépôt GitHub : https://github.com/frank-kenfack/FitHub-Campus

Journal d'avancement : [AVANCEMENT.md](./AVANCEMENT.md)

Tableau de bord interactif : [docs/SUIVI_ETAPES.html](./docs/SUIVI_ETAPES.html)

## SOMMAIRE DES ÉTAPES

1. Étape 1 : `step-01/socle-docker` (Socle Git, PostgreSQL, pile Docker 4 conteneurs et interface initiale)
2. Étape 2 : `step-02/auth-profils-groupes` (Authentification JWT, profils et clubs sportifs)
3. Étape 3 : `step-03/social-fitness` (Stories de séances, photos avant et après et interactions)
4. Étape 4 : `step-04/defis-classements` (Défis intercampus et classements)
5. Étape 5 : `step-05/fitbuddy-realtime` (Matching partenaire et messagerie temps réel)
6. Étape 6 : `step-06/geoloc-gamification` (Carte Leaflet, événements et badges)
7. Étape 7 : `step-07/cicd-qualite-docs` (Pipelines CI/CD GitLab et GitHub, scripts et recette)
8. Étape 8 : `step-08/kubernetes-bonus` (Orchestration Kubernetes, refonte finale et soutenance)

## ÉTAPE 1 : `step-01/socle-docker`

Statut : fusionnée dans `develop` et `main` (`pytest` 5/5, 4 conteneurs actifs).

### 1.1 Vue ordinateur initiale

![Étape 1 : Vue ordinateur](./docs/screenshots/step-01/01-app-desktop.png)

### 1.2 Vue mobile initiale

![Étape 1 : Vue mobile](./docs/screenshots/step-01/02-app-mobile.png)

### 1.3 Point de contrôle `/api/health`

![Étape 1 : Point de contrôle santé API](./docs/screenshots/step-01/03-api-health.png)

### 1.4 Tableau de bord initial

![Étape 1 : Tableau de bord](./docs/screenshots/step-01/04-suivi-dashboard.png)

## ÉTAPE 2 : `step-02/auth-profils-groupes`

Statut : fusionnée dans `develop` et `main` (`pytest` 14/14).

### 2.1 Connexion et inscription

![Étape 2 : Connexion](./docs/screenshots/step-02/01-auth-connexion-desktop.png)

### 2.2 Profil sportif et avatar persistant

![Étape 2 : Profil connecté](./docs/screenshots/step-02/02-profil-avatar-connecte.png)

### 2.3 Clubs sportifs et membres

![Étape 2 : Clubs sportifs](./docs/screenshots/step-02/03-groupes-sportifs-membres.png)

### 2.4 Tableau de bord mis à jour

![Étape 2 : Tableau de bord](./docs/screenshots/step-02/04-suivi-dashboard-step02.png)

## ÉTAPE 3 : `step-03/social-fitness`

Statut : fusionnée dans `develop` et `main` (`pytest` 22/22).

### 3.1 Carrousel et comparatif avant et après

![Étape 3 : Carrousel et comparatif](./docs/screenshots/step-03/01-social-stories-avant-apres.png)

### 3.2 Filtre des séances récentes

![Étape 3 : Séances récentes](./docs/screenshots/step-03/02-social-workout-stories-24h.png)

### 3.3 Formulaire de publication de séance

![Étape 3 : Publication de séance](./docs/screenshots/step-03/03-social-publication-workout.png)

### 3.4 Tableau de bord mis à jour

![Étape 3 : Tableau de bord](./docs/screenshots/step-03/04-suivi-dashboard-step03.png)

## ÉTAPE 4 : `step-04/defis-classements`

Statut : fusionnée dans `develop` et `main` (`pytest` 30/30).

### 4.1 Podium du défi course intercampus

![Étape 4 : Podium défi](./docs/screenshots/step-04/01-defis-podium-campus.png)

### 4.2 Classement général et saisie de performance

![Étape 4 : Classement général](./docs/screenshots/step-04/02-classement-general-et-saisie.png)

### 4.3 Création de défi et défis terminés

![Étape 4 : Création de défi](./docs/screenshots/step-04/03-creation-defi-et-termines.png)

### 4.4 Tableau de bord mis à jour

![Étape 4 : Tableau de bord](./docs/screenshots/step-04/04-suivi-dashboard-step04.png)

## ÉTAPE 5 : `step-05/fitbuddy-realtime`

Statut : fusionnée dans `develop` et `main` (`pytest` 37/37).

### 5.1 Espace partenaire et score d'affinité

![Étape 5 : Espace partenaire](./docs/screenshots/step-05/01-fitbuddy-vue-principale.png)

### 5.2 Session B : envoi d'un encouragement en direct

![Étape 5 : Session B envoi WebSocket](./docs/screenshots/step-05/02-session-sarah-envoi-websocket.png)

### 5.3 Session A : réception instantanée sans rechargement

![Étape 5 : Session A réception live](./docs/screenshots/step-05/03-session-ina-reception-live.png)

### 5.4 Tableau de bord mis à jour

![Étape 5 : Tableau de bord](./docs/screenshots/step-05/04-suivi-dashboard-step05.png)

## ÉTAPE 6 : `step-06/geoloc-gamification`

Statut : fusionnée dans `develop` et `main` (`pytest` 45/45).

### 6.1 Carte interactive Leaflet et rayon de 5 km autour de Lyon

![Étape 6 : Carte interactive Leaflet](./docs/screenshots/step-06/01-carte-leaflet-haversine-lyon.png)

### 6.2 Création d'événement géolocalisé et inscriptions

![Étape 6 : Création événement et inscriptions](./docs/screenshots/step-06/02-creation-evenement-et-rsvp.png)

### 6.3 Récompenses, paliers XP et import Google Fit ou GPX

![Étape 6 : Badges et import Google Fit](./docs/screenshots/step-06/03-badges-paliers-xp-google-fit.png)

### 6.4 Tableau de bord mis à jour

![Étape 6 : Tableau de bord](./docs/screenshots/step-06/04-suivi-dashboard-step06.png)

## ÉTAPE 7 : `step-07/cicd-qualite-docs`

Statut : fusionnée dans `develop` et `main` (`pytest` 51/51, latence de 4 à 31 ms).

### 7.1 Accueil de la plateforme

![Étape 7 : Accueil plateforme](./docs/screenshots/step-07/01-accueil-stack-step07.png)

### 7.2 Profil étudiant avec badges débloqués

![Étape 7 : Profil étudiant et badges](./docs/screenshots/step-07/02-profil-etudiant-badges-actifs.png)

### 7.3 Rapport de recette, pipelines et latence

![Étape 7 : Rapport qualité et latence](./docs/screenshots/step-07/03-rapport-qualite-latence-cicd.png)

### 7.4 Tableau de bord mis à jour

![Étape 7 : Tableau de bord](./docs/screenshots/step-07/04-suivi-dashboard-step07.png)

## ÉTAPE 8 : `step-08/kubernetes-bonus`

Statut : fusionnée dans `develop` et `main`, version `v1.0.0` (`pytest` 58/58, `kubectl kustomize k8s/` valide).

### 8.1 Accueil final refondu en Times New Roman

![Étape 8 : Accueil final refondu](./docs/screenshots/step-08/01-accueil-final-step08.png)

### 8.2 Topologie des 14 ressources Kubernetes et scénario jury

![Étape 8 : Topologie Kubernetes et jury](./docs/screenshots/step-08/02-topologie-kubernetes-et-jury.png)

### 8.3 Vue mobile responsive

![Étape 8 : Vue mobile responsive](./docs/screenshots/step-08/03-vue-mobile-first-responsive.png)

### 8.4 Tableau de bord final (100 %)

![Étape 8 : Tableau de bord final](./docs/screenshots/step-08/04-suivi-dashboard-final-100pct.png)
