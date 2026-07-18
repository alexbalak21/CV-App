import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
PHOTOS_DIR = INSTANCE_DIR / "storage" / "photos"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # hard cap on any request body (2 MB)
    PHOTO_MAX_UPLOAD_BYTES = 1 * 1024 * 1024  # 1 MB, enforced again in photo_service
    PHOTOS_DIR = str(PHOTOS_DIR)


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIG_MAP = {
    "dev": DevConfig,
    "prod": ProdConfig,
}
