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
    # pool_pre_ping: issues a cheap "is this connection still alive" check
    # before handing it out, transparently reconnecting if not. Without
    # this, MySQL silently closing idle connections after `wait_timeout`
    # (default 8h, but can be much shorter on shared hosts) surfaces as a
    # random "Lost connection to MySQL server during query" mid-request.
    # pool_recycle: proactively discards connections older than this many
    # seconds, as a belt-and-suspenders complement to pool_pre_ping.
    # Harmless no-ops on SQLite.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
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
