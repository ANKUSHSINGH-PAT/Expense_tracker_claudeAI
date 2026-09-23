# Spec: Registration Claude

## Overview
Step 02 made `POST /register` work, but the flow still has gaps a real user would hit. `register.html` and `login.html` both override `{% block flash %}` with an empty block, so every validation error ("Passwords do not match", "Email already registered", …) and the "Account created! Please sign in." success message are silently swallowed. The password field promises "Min. 8 characters" but the server accepts any length. Emails are stored exactly as typed, so `Demo@Spendly.com` and `demo@spendly.com` become two separate accounts and the mixed-case one can't log in with the lowercase address. And on any error the form comes back empty, forcing the user to retype everything. This step hardens registration so errors are visible, input is validated and normalised, and the form keeps what the user typed.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user()`, `POST /register`)
- Step 03 — Login and Logout (`POST /login`, `get_user_by_email()`)

## Routes
No new routes. `GET /register` and `POST /register` in `app.py` are modified:
- `GET /register` — render empty form (`form={}`) — public
- `POST /register` — validate, normalise, create user, redirect to `/login` — public

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`) is sufficient.

Email normalisation happens before insert and before lookup:
- `create_user(name, email, password)` in `database/db.py` stores `email.strip().lower()`
- `get_user_by_email(email)` in `database/db.py` looks up `email.strip().lower()`

Existing mixed-case rows (if any) are not migrated.

## Templates
- **Create:** none
- **Modify:** `templates/register.html`
  - Remove the empty `{% block flash %}{% endblock %}` override so flashed messages render via `base.html`, **or** replace it with an in-card error block using the existing `.auth-error` class — pick one and use it for both auth pages
  - Repopulate `name` and `email` inputs from `form` on re-render: `value="{{ form.get('name', '') }}"`, `value="{{ form.get('email', '') }}"`
  - Never repopulate `password` / `confirm_password`
  - Add `minlength="8"` to both password inputs (client-side hint only — server remains the source of truth)
- **Modify:** `templates/login.html`
  - Same flash fix as `register.html`, so the "Account created! Please sign in." message is visible after redirect

## Files to change
- `app.py` — `register()`: add min-length and email-format checks, normalise email, pass `form=request.form` on every error re-render and `form={}` on GET
- `database/db.py` — lowercase/strip email in `create_user()` and `get_user_by_email()`
- `templates/register.html` — flash display, value repopulation, `minlength`
- `templates/login.html` — flash display
- `static/css/style.css` — only if a new style is needed for the chosen flash placement (use existing variables)

## Files to create
- `templates/_auth_flash.html` — shared include that renders flashed messages inside `.auth-card` on register and login
- `tests/test_10_registration.py` — pytest coverage for the definition of done below

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with werkzeug (`generate_password_hash`) — never plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `url_for()` for every internal link
- DB logic stays in `database/db.py` — the route only calls helpers
- Server-side validation order in `register()` (first failure wins, re-render with `form=request.form`, no redirect):
  1. All fields non-empty → "All fields are required."
  2. Email has the shape `something@something.something` (simple check, no regex library, no network lookup) → "Please enter a valid email address."
  3. `len(password) >= 8` → "Password must be at least 8 characters."
  4. `password == confirm_password` → "Passwords do not match."
  5. `sqlite3.IntegrityError` from `create_user()` → "Email already registered."
- Name is `.strip()`ed; password is never stripped
- Do not change login validation rules beyond the email normalisation in `get_user_by_email()` — the seeded `demo@spendly.com` / `demo123` account must still log in even though its password is under 8 characters

## Definition of done
- [ ] `GET /register` renders the form with empty fields and no errors
- [ ] Submitting with an empty field shows "All fields are required." on the page
- [ ] Submitting `not-an-email` shows "Please enter a valid email address."
- [ ] Submitting a 7-character password shows "Password must be at least 8 characters."
- [ ] Submitting mismatched passwords shows "Passwords do not match."
- [ ] Submitting an already-registered email shows "Email already registered."
- [ ] On every error above, the name and email fields keep what was typed; password fields are empty
- [ ] On every error above, no row is inserted into `users`
- [ ] Registering `New.User@Example.com` stores `new.user@example.com` in `spendly.db`
- [ ] After that, registering `new.user@example.com` fails with "Email already registered."
- [ ] That user can log in with `NEW.USER@example.com` and the correct password
- [ ] A successful registration redirects to `/login` and the page shows "Account created! Please sign in."
- [ ] A logged-in user visiting `/register` is still redirected to `/profile`
- [ ] `demo@spendly.com` / `demo123` still logs in
- [ ] Stored `password_hash` is a werkzeug hash, not the plaintext password
- [ ] `pytest` passes, including the new `tests/test_10_registration.py`
