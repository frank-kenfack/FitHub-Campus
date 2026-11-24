# FITHUB CAMPUS : GUIDE DE SOUTENANCE JURY (15 MINUTES)

Ce conducteur organise la présentation orale de quinze minutes : cinq minutes sur l'architecture et l'automatisation, sept minutes de démonstration directe et trois minutes de questions techniques.

## 1. VÉRIFICATIONS AVANT SOUTENANCE

Lancez la pile locale et vérifiez les quatre conteneurs :

```bash
./scripts/deploy.sh
```

Ouvrez ensuite `http://localhost:8080` dans deux fenêtres séparées pour illustrer les échanges entre `InaFit_Lyon` et `SarahRun_Bdx` sur l'onglet « Partenaires ». Gardez ouverts dans d'autres onglets `docs/SUIVI_ETAPES.html`, `docs/RAPPORT_KUBERNETES_STEP08.html` et `docs/RAPPORT_QUALITE_STEP07.html`.

## 2. DÉROULEMENT CHRONOMÉTRÉ

### Architecture et automatisation (00:00 à 05:00)

Présentez le découpage du backlog (`FitHub_Campus_Backlog_MVP.pdf`) et la séparation des huit branches dans Gitflow. Montrez ensuite le fichier `docker-compose.yml` qui isole la base PostgreSQL 16 et Redis 7 sur `fithub_net`, puis les pipelines `.gitlab-ci.yml`, `.github/workflows/ci.yml` et la pile Kubernetes sous `k8s/` (deux réplicas pour le serveur et l'interface, deux volumes persistants et un Ingress WebSocket).

### Démonstration applicative (05:00 à 12:00)

1. Sur l'accueil, connectez `InaFit_Lyon` en un clic pour afficher ses compteurs, le classement intercampus et les défis en cours.
2. Dans « Clubs » et « Fil social », montrez l'adhésion à un club, la publication de séance et le curseur comparatif avant et après.
3. Dans « Défis », ajoutez une performance pour actualiser le podium du campus en direct.
4. Dans « Partenaires », envoyez un message depuis la seconde fenêtre pour montrer l'apparition immédiate de l'encouragement et de la série active dans la première fenêtre.
5. Terminez par « Carte et lieux » (filtre à 5 km autour de Lyon et inscription à une séance collective) puis « Récompenses » (import Google Fit ou GPX et vitrine des badges).

### Réponses aux questions techniques (12:00 à 15:00)

| Question possible du jury | Réponse factuelle |
| :--- | :--- |
| Comment fonctionne le temps réel avec deux réplicas Kubernetes ? | Flask-SocketIO utilise Redis Pub/Sub (`message_queue=REDIS_URL`). Un événement émis sur un pod est transmis à tous les autres pods abonnés à la room `user_<id>`. |
| Comment évitez-vous le dépassement de capacité lors d'inscriptions simultanées ? | La base applique la contrainte d'unicité `uq_event_rsvp` et le serveur pose un verrou pessimiste `with_for_update()` sur l'événement avant de contrôler `max_participants`. |
| Comment sont sécurisés les fichiers envoyés par les utilisateurs ? | Les images sont vérifiées et ré-encodées par Pillow sous un nom aléatoire UUID4 ; les traces `.gpx` contenant `<!DOCTYPE` ou `<!ENTITY` sont rejetées avant lecture XML. |
| Comment vérifiez-vous la limite de latence sous 300 ms ? | La suite `test_step07_quality_perf.py` et le script `scripts/smoke_test.sh` mesurent chaque route critique derrière Nginx. |
