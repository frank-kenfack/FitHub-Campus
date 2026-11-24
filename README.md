# FITHUB CAMPUS

FitHub Campus est un réseau social sportif destiné aux étudiants. Il permet de créer des clubs par campus, de publier des séances avec photos comparatives, de participer à des défis intercampus, de trouver un partenaire d'entraînement en direct et de localiser les salles et rendez-vous sportifs.

## INSTALLATION

Docker et Docker Compose doivent être installés sur la machine.

```bash
cp .env.example .env
```

Les variables par défaut du fichier `.env.example` permettent un démarrage local immédiat sans modification.

## LANCEMENT

Démarrez les quatre services de l'application avec la commande suivante :

```bash
docker compose up --build -d --wait
```

L'application est ensuite accessible sur `http://localhost:8080`. Pour exécuter la suite de tests automatisés dans le conteneur serveur :

```bash
docker compose exec -T backend pytest -v
```
