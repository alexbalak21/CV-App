import io
import json

from app.models import CV, CVVersion, User
from app.extensions import db


def _login(client, registered_user):
    client.post(
        "/auth/login",
        data={"email": registered_user["email"], "password": registered_user["password"]},
    )


def _create_cv(client, title="Test CV"):
    return client.post("/cvs/new", data={"title": title, "template_slug": "classic_sidebar"})


def test_create_cv_creates_version_1(client, registered_user, app):
    _login(client, registered_user)
    resp = _create_cv(client)
    assert resp.status_code == 302

    with app.app_context():
        cv = CV.query.first()
        assert cv is not None
        assert cv.title == "Test CV"
        versions = CVVersion.query.filter_by(cv_id=cv.id).all()
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert cv.current_version_id == versions[0].id


def test_save_creates_new_version_without_deleting_old(client, registered_user, app):
    _login(client, registered_user)
    _create_cv(client)

    with app.app_context():
        cv_id = CV.query.first().id

    payload = {"data": {"header": {"fullName": "New Name", "jobTitle": "", "photo": "", "links": []}}}
    resp = client.post(f"/cvs/{cv_id}/save", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["version_number"] == 2

    with app.app_context():
        versions = CVVersion.query.filter_by(cv_id=cv_id).order_by(CVVersion.version_number).all()
        assert len(versions) == 2
        assert versions[0].data is not None  # old version still there
        assert versions[1].data["header"]["fullName"] == "New Name"

        cv = db.session.get(CV, cv_id)
        assert cv.current_version_id == versions[1].id


def test_restore_version_creates_new_version_not_rollback(client, registered_user, app):
    _login(client, registered_user)
    _create_cv(client)
    with app.app_context():
        cv_id = CV.query.first().id
        v1_id = CVVersion.query.filter_by(cv_id=cv_id, version_number=1).first().id

    client.post(f"/cvs/{cv_id}/save", json={"data": {"header": {"fullName": "V2", "jobTitle": "", "photo": "", "links": []}}})

    resp = client.post(f"/cvs/{cv_id}/versions/{v1_id}/restore")
    assert resp.status_code == 302

    with app.app_context():
        versions = CVVersion.query.filter_by(cv_id=cv_id).order_by(CVVersion.version_number).all()
        assert len(versions) == 3  # nothing deleted, a new v3 was appended
        assert versions[2].label.startswith("Restauré")
        cv = db.session.get(CV, cv_id)
        assert cv.current_version_id == versions[2].id


def test_user_cannot_access_other_users_cv(client, app):
    # user A creates a CV
    client.post("/auth/register", data={
        "email": "a@test.dev", "display_name": "A",
        "password": "testpass123", "confirm_password": "testpass123",
    })
    _create_cv(client, title="A's CV")
    client.post("/auth/logout")

    with app.app_context():
        cv_id = CV.query.first().id

    # user B logs in and tries to access it
    client.post("/auth/register", data={
        "email": "b@test.dev", "display_name": "B",
        "password": "testpass123", "confirm_password": "testpass123",
    })
    resp = client.get(f"/cvs/{cv_id}/edit")
    assert resp.status_code == 404


def test_render_preview_returns_html(client, registered_user):
    _login(client, registered_user)
    _create_cv(client)
    data = {
        "header": {"fullName": "Alex Test", "jobTitle": "Dev", "photo": "", "links": []},
        "profile": {"title": "Profil", "text": "**Bold** text"},
        "contact": {"title": "Contact", "items": []},
        "skills": {"title": "Skills", "items": ["[fa:solid:database] SQL"]},
        "certifications": {"title": "Certs", "items": []},
        "languages": {"title": "Langues", "items": []},
        "hobbies": {"title": "Hobbies", "items": []},
        "experience": {"title": "Exp", "items": []},
        "education": {"title": "Edu", "items": []},
    }
    resp = client.post("/cvs/1/render-preview", json={"data": data})
    assert resp.status_code == 200
    html = resp.get_json()["html"]
    assert "Alex Test" in html
    assert "<strong>Bold</strong>" in html
    assert 'fa-solid fa-database' in html


def test_render_preview_escapes_html_injection(client, registered_user):
    _login(client, registered_user)
    _create_cv(client)
    data = {
        "header": {"fullName": "<script>alert(1)</script>", "jobTitle": "", "photo": "", "links": []},
        "profile": {"title": "P", "text": ""},
        "contact": {"title": "C", "items": []},
        "skills": {"title": "S", "items": []},
        "certifications": {"title": "Ce", "items": []},
        "languages": {"title": "L", "items": []},
        "hobbies": {"title": "H", "items": []},
        "experience": {"title": "E", "items": []},
        "education": {"title": "Ed", "items": []},
    }
    resp = client.post("/cvs/1/render-preview", json={"data": data})
    html = resp.get_json()["html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_photo_storage_path_uses_forward_slash(client, registered_user, app, tmp_path):
    """Regression test: storage_path must never contain a backslash.

    Werkzeug's safe_join() (used internally by send_from_directory in
    serve_photo) silently rejects any path containing a backslash on
    Windows, turning it into a 404 with nothing logged as an error. This
    only reproduces on Windows (os.sep == '\\'), which is why it's asserted
    directly on the string rather than relying on a live 404 in CI.
    """
    _login(client, registered_user)
    _create_cv(client)

    app.config["PHOTOS_DIR"] = str(tmp_path)
    img_bytes = _make_test_jpeg_bytes()

    resp = client.post(
        "/cvs/1/photo",
        data={"variant": "200", "photo": (io.BytesIO(img_bytes), "test.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200

    with app.app_context():
        from app.models import Photo
        photo = Photo.query.first()
        assert photo is not None
        assert "\\" not in photo.storage_path, (
            f"storage_path contains a backslash: {photo.storage_path!r} — "
            "this will 404 on Windows via safe_join()"
        )
        assert "/" in photo.storage_path


def test_uploaded_photo_is_immediately_servable(client, registered_user, app, tmp_path):
    _login(client, registered_user)
    _create_cv(client)

    app.config["PHOTOS_DIR"] = str(tmp_path)
    img_bytes = _make_test_jpeg_bytes()

    upload_resp = client.post(
        "/cvs/1/photo",
        data={"variant": "200", "photo": (io.BytesIO(img_bytes), "test.jpg")},
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 200
    photo_url = upload_resp.get_json()["url"]

    get_resp = client.get(photo_url)
    assert get_resp.status_code == 200
    assert get_resp.content_type == "image/jpeg"


def test_serve_photo_normalizes_legacy_backslash_paths(client, registered_user, app, tmp_path):
    """Rows created before the storage_path fix may have backslashes
    (Windows os-native separator). serve_photo should normalize and still
    find the file rather than 404 forever on old data."""
    _login(client, registered_user)
    _create_cv(client)
    app.config["PHOTOS_DIR"] = str(tmp_path)

    with app.app_context():
        from app.extensions import db
        from app.models import Photo

        user_dir = tmp_path / "1"
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "legacy.jpg").write_bytes(_make_test_jpeg_bytes())

        legacy_photo = Photo(
            user_id=1,
            storage_path="1\\legacy.jpg",  # simulates a pre-fix Windows row
            variant="200",
            width=200,
            height=200,
            filesize_bytes=100,
        )
        db.session.add(legacy_photo)
        db.session.commit()
        photo_id = legacy_photo.id

    resp = client.get(f"/cvs/photos/{photo_id}")
    assert resp.status_code == 200


def _make_test_jpeg_bytes() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), color=(120, 140, 200)).save(buf, format="JPEG")
    return buf.getvalue()
