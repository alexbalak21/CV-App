import os
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
PHOTOS_DIR = INSTANCE_DIR / "storage" / "photos"
CV_TEMPLATES_DIR = BASE_DIR / "app" / "storage" / "cv_templates"


def _build_database_uri() -> str:
    """
    Resolve the SQLAlchemy database URI, in priority order:

    1. DATABASE_URL, if set — a full SQLAlchemy connection string.
    2. DATABASE_HOST/PORT/USER/PASSWORD/NAME component variables — used if
       DATABASE_NAME is set, since that's the one value with no sensible
       default. Always connects via PyMySQL with utf8mb4.
    3. A local SQLite file under instance/, if neither is set.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    db_name = os.environ.get("DATABASE_NAME")
    if db_name:
        host = os.environ.get("DATABASE_HOST", "localhost")
        port = os.environ.get("DATABASE_PORT", "3306")
        user = os.environ.get("DATABASE_USER") or "root"
        password = os.environ.get("DATABASE_PASSWORD") or ""

        # URL-encode user/password so special characters (@, :, /, etc.)
        # don't get misparsed as URI delimiters.
        user_enc = quote_plus(user)
        password_enc = quote_plus(password)

        return (
            f"mysql+pymysql://{user_enc}:{password_enc}@{host}:{port}"
            f"/{db_name}?charset=utf8mb4"
        )

    return f"sqlite:///{INSTANCE_DIR / 'app.db'}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
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
    CV_TEMPLATES_DIR = str(CV_TEMPLATES_DIR)


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIG_MAP = {
    "dev": DevConfig,
    "prod": ProdConfig,
}
