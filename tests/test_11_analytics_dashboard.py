"""
Tests for Step 11: Analytics Dashboard
Spec: .claude/specs/11-analytics-dashboard.md

Covers:
- GET /analytics auth guard (logged out → 302 /login)
- Logged-in page renders real data, not the "Coming Soon" placeholder
- Summary stats (total, count, top category)
- Donut segments: one per category, lengths sum to 100
- Legend lists categories with amount and percent, largest first
- Other users' expenses are never included
- Empty state for a user with no expenses
- Analytics navbar link is active
"""

import re

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from app import app as flask_app
from database.db import init_db

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


def _create_user(name, email):
    conn = db_module.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash("password123")),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def _add_expenses(user_id, rows):
    conn = db_module.get_db()
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        [(user_id, amt, cat, "2026-09-01", "test") for amt, cat in rows],
    )
    conn.commit()
    conn.close()


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Test User"


def _segments(html):
    """Return [(category, dash_length)] for each donut segment."""
    return [
        (cat, int(length))
        for cat, length in re.findall(
            r'donut-seg donut-seg--(\w+)"[^>]*?stroke-dasharray="(\d+) ', html, re.S
        )
    ]


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


def test_logged_out_redirects_to_login(client):
    resp = client.get("/analytics")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


# ---------------------------------------------------------------------------
# Dashboard content
# ---------------------------------------------------------------------------


@pytest.fixture
def user_with_expenses(client):
    uid = _create_user("Test User", "test@example.com")
    _add_expenses(
        uid,
        [
            (600.00, "Food"),
            (400.00, "Food"),
            (500.00, "Bills"),
            (250.00, "Transport"),
            (250.00, "Other"),
        ],
    )
    _login(client, uid)
    return uid


def test_page_renders_without_placeholder(client, user_with_expenses):
    resp = client.get("/analytics")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Coming Soon" not in html
    assert "Spending by Category" in html


def test_summary_stats(client, user_with_expenses):
    html = client.get("/analytics").get_data(as_text=True)

    assert "₹2,000.00" in html  # total
    assert re.search(r'stat-label">Transactions</span>\s*<span class="stat-value">5<', html)
    assert re.search(r'stat-label">Top Category</span>\s*<span class="stat-value">Food<', html)


def test_donut_has_one_segment_per_category_summing_to_100(client, user_with_expenses):
    html = client.get("/analytics").get_data(as_text=True)
    segments = _segments(html)

    # Food 1000 (50%), Bills 500 (25%), Transport 250, Other 250 (12% each);
    # the rounding remainder goes to the largest category.
    assert [cat for cat, _ in segments][:2] == ["food", "bills"]
    assert dict(segments) == {"food": 51, "bills": 25, "transport": 12, "other": 12}
    assert sum(length for _, length in segments) == 100


def test_total_shown_in_donut_center(client, user_with_expenses):
    html = client.get("/analytics").get_data(as_text=True)

    assert re.search(r'donut-center-value">₹2,000.00<', html)


def test_legend_lists_categories_largest_first(client, user_with_expenses):
    html = client.get("/analytics").get_data(as_text=True)
    legend = html[html.index('class="donut-legend"'):]

    assert "₹1,000.00 · 51%" in legend
    assert "₹500.00 · 25%" in legend
    assert "₹250.00 · 12%" in legend
    assert legend.index("Food") < legend.index("Bills") < legend.index("Transport")
    assert legend.index("Bills") < legend.index("Other")


def test_other_users_expenses_excluded(client, user_with_expenses):
    other = _create_user("Other User", "other@example.com")
    _add_expenses(other, [(9999.00, "Entertainment")])

    html = client.get("/analytics").get_data(as_text=True)

    assert "9,999.00" not in html
    assert "donut-seg--entertainment" not in html
    assert "₹2,000.00" in html


def test_analytics_nav_link_active(client, user_with_expenses):
    html = client.get("/analytics").get_data(as_text=True)

    assert re.search(r'href="/analytics" class="nav-link-active"', html)


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


def test_empty_state_for_user_without_expenses(client):
    uid = _create_user("Empty User", "empty@example.com")
    _login(client, uid)

    resp = client.get("/analytics")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "No expenses yet" in html
    assert 'class="donut"' not in html
    assert 'href="/expenses/add"' in html
    assert "₹0.00" in html
