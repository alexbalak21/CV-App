import pytest

from app import create_app
from app.extensions import db as _db
from scripts.seed_templates import run as seed_templates


@pytest.fixture()
def app():
    app = create_app("dev", overrides={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        _db.create_all()
        seed_templates()
        yield app
        _db.session.remove()
        # cvs.current_version_id <-> cv_versions.cv_id is a circular FK
        # (by design, see plan.md); SQLite's drop_all() can't resolve the
        # drop order on its own, so disable FK checks just for teardown.
        _db.session.execute(_db.text("PRAGMA foreign_keys=OFF"))
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def registered_user(client):
    client.post(
        "/auth/register",
        data={
            "email": "alex@test.dev",
            "display_name": "Alex",
            "password": "testpass123",
            "confirm_password": "testpass123",
        },
        follow_redirects=True,
    )
    return {"email": "alex@test.dev", "password": "testpass123"}
