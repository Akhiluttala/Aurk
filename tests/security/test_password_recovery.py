import re
from unittest.mock import Mock

import pytest
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User, Role
from app.auth import routes


@pytest.fixture
def recovery(app, monkeypatch):
    with app.app_context():
        db.session.add(User(email="admin@example.com", first_name="Store", last_name="Owner",
            password_hash=generate_password_hash("OriginalPassword123!"), roles=[Role(name="Admin")]))
        db.session.commit()
    sender = Mock()
    monkeypatch.setattr(routes, "send_email", sender)
    app.config["PUBLIC_BASE_URL"] = "https://store.example.com"
    return sender


def reset_path(client, sender):
    response = client.post("/auth/forgot-password?admin=1", data={"email": "admin@example.com"})
    assert b"Check your email" in response.data
    return re.search(r'/auth/reset-password/([^"< ]+)', sender.call_args.args[2]).group(0)


def test_admin_email_reset_and_single_use(client, recovery):
    page = client.get("/admin/login")
    assert b"/auth/forgot-password?admin=1" in page.data
    path = reset_path(client, recovery)
    assert "https://store.example.com" in recovery.call_args.args[3]
    page = client.get(path)
    assert page.status_code == 200
    assert page.headers["Referrer-Policy"] == "no-referrer"
    assert page.headers["Cache-Control"] == "no-store, private"
    assert b"confirm_password" in page.data
    response = client.post(path, data={"password": "NewAdminPassword123!", "confirm_password": "NewAdminPassword123!"})
    assert response.location == "/admin/login"
    assert client.get(path).status_code == 302
    response = client.post("/admin/login", data={"email": "admin@example.com", "password": "NewAdminPassword123!"})
    assert response.location == "/admin/dashboard"


@pytest.mark.parametrize("password,confirmation", [("short", "short"), ("NewPassword123!", "mismatch"), ("x" * 1025, "x" * 1025)])
def test_invalid_password_preserves_account(client, recovery, password, confirmation):
    path = reset_path(client, recovery)
    assert client.post(path, data={"password": password, "confirm_password": confirmation}).status_code == 200
    with client.application.app_context():
        assert check_password_hash(User.query.one().password_hash, "OriginalPassword123!")


def test_unknown_email_and_smtp_failure_show_same_confirmation(client, recovery):
    unknown = client.post("/auth/forgot-password?admin=1", data={"email": "unknown@example.com"})
    recovery.assert_not_called()
    recovery.side_effect = RuntimeError("SMTP unavailable")
    known = client.post("/auth/forgot-password?admin=1", data={"email": "admin@example.com"})
    assert unknown.data == known.data
    assert known.status_code == 200


def test_invalid_expired_token_and_csrf(client, recovery, monkeypatch):
    assert client.get("/auth/reset-password/tampered").location == "/auth/forgot-password"
    path = reset_path(client, recovery)
    monkeypatch.setattr(routes, "read_token", Mock(side_effect=ValueError("Expired")))
    assert client.get(path).location == "/auth/forgot-password"
    client.application.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/auth/forgot-password", data={"email": "admin@example.com"}).status_code == 400


def test_reset_url_uses_configured_domain(client, recovery):
    client.post("/auth/forgot-password", data={"email": "admin@example.com"}, headers={"Host": "attacker.example"})
    assert "attacker.example" not in recovery.call_args.args[3]
    assert "https://store.example.com" in recovery.call_args.args[3]
