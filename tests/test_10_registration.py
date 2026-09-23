"""
Tests for Step 10: Registration Claude
Spec: .claude/specs/10-registration-claude.md

Covers:
- GET /register renders an empty form
- Each validation error is shown on the page, keeps name/email, never echoes
  the password, and inserts no row
- Validation order (first failure wins)
- Duplicate email, including case-only differences
- Email is stored lowercase and login works with any casing
- Successful registration redirects to /login and shows the success message
- Logged-in users are redirected away from /register
- Seeded demo account still logs in
- Passwords are stored as werkzeug hashes
"""

import pytest
from werkzeug.security import check_password_hash

import database.db as db_module
from app import app as flask_app
from database.db import get_user_by_email, init_db, seed_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_spendly.db")


@pytest.fixture
def app(db_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.app_context():
        init_db()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID = {
    "name": "New User",
    "email": "new@example.com",
    "password": "password123",
    "confirm_password": "password123",
}


def _post(client, follow_redirects=False, **overrides):
    data = {**VALID, **overrides}
    return client.post("/register", data=data, follow_redirects=follow_redirects)


def _count_users():
    conn = db_module.get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count


def _get_row(email):
    conn = db_module.get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


# ---------------------------------------------------------------------------
# GET /register
# ---------------------------------------------------------------------------


def test_get_register_renders_empty_form(client):
    resp = client.get("/register")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert 'name="name"' in html
    assert 'value=""' in html
    assert "auth-error" not in html


def test_logged_in_user_redirected_from_register(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Someone"

    resp = client.get("/register")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"name": ""}, "All fields are required."),
        ({"email": ""}, "All fields are required."),
        ({"password": "", "confirm_password": ""}, "All fields are required."),
        ({"confirm_password": ""}, "All fields are required."),
        ({"email": "not-an-email"}, "Please enter a valid email address."),
        ({"email": "a@b"}, "Please enter a valid email address."),
        ({"email": "@x.com"}, "Please enter a valid email address."),
        ({"email": "a@.com"}, "Please enter a valid email address."),
        ({"email": "a@x.com."}, "Please enter a valid email address."),
        ({"email": "a@@x.com"}, "Please enter a valid email address."),
        ({"email": "a b@x.com"}, "Please enter a valid email address."),
        (
            {"password": "short12", "confirm_password": "short12"},
            "Password must be at least 8 characters.",
        ),
        ({"confirm_password": "different123"}, "Passwords do not match."),
    ],
)
def test_validation_errors(client, overrides, message):
    resp = _post(client, **overrides)
    html = resp.get_data(as_text=True)
    data = {**VALID, **overrides}

    assert resp.status_code == 200
    assert message in html
    assert "auth-error" in html
    assert _count_users() == 0

    # Name and email are kept (if they were provided)
    if data["name"]:
        assert f'value="{data["name"]}"' in html
    if data["email"] and " " not in data["email"]:
        assert f'value="{data["email"]}"' in html

    # Passwords are never echoed back
    if data["password"]:
        assert data["password"] not in html
    if data["confirm_password"]:
        assert data["confirm_password"] not in html


def test_short_password_checked_before_mismatch(client):
    resp = _post(client, password="short12", confirm_password="other12")
    html = resp.get_data(as_text=True)

    assert "Password must be at least 8 characters." in html
    assert "Passwords do not match." not in html


def test_repopulated_values_are_escaped(client):
    resp = _post(client, name='Evil "User"', email="bad")
    html = resp.get_data(as_text=True)

    assert 'value="Evil &#34;User&#34;"' in html


# ---------------------------------------------------------------------------
# Duplicate email and normalisation
# ---------------------------------------------------------------------------


def test_duplicate_email_rejected(client):
    _post(client)
    resp = _post(client, name="Other Person")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Email already registered." in html
    assert _count_users() == 1


def test_email_stored_lowercase(client):
    _post(client, email="New.User@Example.com")

    assert _get_row("new.user@example.com") is not None
    assert _get_row("New.User@Example.com") is None


def test_case_only_duplicate_rejected(client):
    _post(client, email="New.User@Example.com")
    resp = _post(client, email="new.user@example.com")

    assert "Email already registered." in resp.get_data(as_text=True)
    assert _count_users() == 1


def test_login_with_different_casing(client):
    _post(client, email="New.User@Example.com")

    resp = client.post(
        "/login",
        data={"email": "NEW.USER@example.com", "password": VALID["password"]},
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_get_user_by_email_normalises(app):
    seed_db()

    user = get_user_by_email("  DEMO@Spendly.com ")

    assert user is not None
    assert user["email"] == "demo@spendly.com"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_successful_registration_redirects_to_login(client):
    resp = _post(client)

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    assert _count_users() == 1


def test_success_message_shown_on_login_page(client):
    resp = _post(client, follow_redirects=True)
    html = resp.get_data(as_text=True)

    assert resp.request.path == "/login"
    assert "Account created! Please sign in." in html
    assert "auth-success" in html


def test_password_stored_as_hash(client):
    _post(client)
    row = _get_row(VALID["email"])

    assert row["password_hash"] != VALID["password"]
    assert check_password_hash(row["password_hash"], VALID["password"])


# ---------------------------------------------------------------------------
# Login regressions
# ---------------------------------------------------------------------------


def test_demo_user_still_logs_in(client):
    seed_db()

    resp = client.post(
        "/login", data={"email": "demo@spendly.com", "password": "demo123"}
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_login_error_shown_and_email_kept(client):
    resp = client.post(
        "/login", data={"email": "nobody@example.com", "password": "wrongpass"}
    )
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Invalid email or password." in html
    assert 'value="nobody@example.com"' in html
    assert "wrongpass" not in html
