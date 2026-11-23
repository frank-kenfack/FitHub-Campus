"""Configuration de l'application FitHub Campus."""

import os


def _normalize_db_url(raw_url: str) -> str:
    """Force le pilote psycopg2 pour les URL PostgreSQL standard."""
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


class Config:
    """Configuration par defaut chargee depuis les variables d'environnement."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get(
            "DATABASE_URL",
            "postgresql://fithub_user:fithub_dev_pwd@db:5432/fithub",
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/app/uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 Mo


class TestingConfig(Config):
    """Configuration dediee a la suite de tests Pytest."""

    TESTING = True
