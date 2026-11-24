#!/bin/sh
set -e

echo "[FitHub Backend] Application des migrations PostgreSQL..."
flask --app wsgi:app db upgrade

echo "[FitHub Backend] Initialisation des donnees de reference (seed)..."
python -m app.seed

echo "[FitHub Backend] Demarrage du serveur Gunicorn (eventlet)..."
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 gunicorn_wsgi:app
