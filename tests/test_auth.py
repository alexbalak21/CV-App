def test_register_then_redirect_to_cv_list(client):
    resp = client.post(
        "/auth/register",
        data={
            "email": "new@test.dev",
            "display_name": "New User",
            "password": "testpass123",
            "confirm_password": "testpass123",
        },
    )
    assert resp.status_code == 302
    assert "/cvs" in resp.headers["Location"]


def test_register_duplicate_email_rejected(client, registered_user):
    client.post("/auth/logout")
    resp = client.post(
        "/auth/register",
        data={
            "email": registered_user["email"],
            "display_name": "Dup",
            "password": "testpass123",
            "confirm_password": "testpass123",
        },
    )
    assert resp.status_code == 200  # re-renders form with flash error
    assert b"existe d" in resp.data or b"compte existe" in resp.data.lower() or "existe".encode() in resp.data


def test_login_wrong_password_rejected(client, registered_user):
    client.post("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"email": registered_user["email"], "password": "wrongpass"},
    )
    assert resp.status_code == 200
    assert "incorrect".encode() in resp.data.lower() or b"incorrect" in resp.data


def test_login_success(client, registered_user):
    client.post("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 302


def test_cvs_requires_login(client):
    resp = client.get("/cvs/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
