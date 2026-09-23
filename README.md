# Spendly

A lightweight personal expense tracker built with **Flask** and **SQLite**.

Register, log your daily expenses, and see where your money goes, with summary stats, a category breakdown, and date-range filters.

## Features

- **Accounts:** register, log in, and log out, with hashed passwords via Werkzeug
- **Add expenses:** amount, category, date, and an optional description
- **Edit and delete:** change or remove your own expenses; deleting asks for confirmation
- **Profile dashboard:** summary stats, recent transactions, and spending by category
- **Date filters:** a custom date range or quick presets (this month, last 3 months, last 6 months)
- **Categories:** Food, Transport, Bills, Health, Entertainment, Shopping, Other

## Tech stack

| Layer    | Choice                                |
|----------|---------------------------------------|
| Backend  | Flask 3 (single `app.py`, no blueprints) |
| Database | SQLite through the `sqlite3` module (no ORM) |
| Frontend | Jinja2 templates, plain CSS, vanilla JS |
| Tests    | pytest + pytest-flask                 |

## Getting started

Requires **Python 3.10+**.

```bash
git clone https://github.com/ANKUSHSINGH-PAT/Expense_tracker_claudeAI.git
cd Expense_tracker_claudeAI

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python app.py
```

Open <http://localhost:5001>. The app runs on port **5001**, not Flask's default 5000.

On first run the database is created automatically and seeded with a demo account:

| Email              | Password  |
|--------------------|-----------|
| `demo@spendly.com` | `demo123` |

## Project structure

```
spendly/
├── app.py              # All routes
├── database/
│   ├── db.py           # Connection, schema, seeding, user helpers
│   └── queries.py      # Expense and dashboard queries
├── templates/          # Jinja2 pages, all extending base.html
├── static/
│   ├── css/            # Global and page-specific styles
│   └── js/main.js      # Vanilla JS
├── tests/              # pytest suites
└── requirements.txt
```

## Routes

| Method     | Route                     | Description                    |
|------------|---------------------------|--------------------------------|
| GET        | `/`                       | Landing page                   |
| GET, POST  | `/register`               | Create an account              |
| GET, POST  | `/login`                  | Log in                         |
| GET        | `/logout`                 | Log out                        |
| GET        | `/profile`                | Dashboard with date filters    |
| GET        | `/analytics`              | Analytics page                 |
| GET, POST  | `/expenses/add`           | Add an expense                 |
| GET, POST  | `/expenses/<id>/edit`     | Edit an expense                |
| POST       | `/expenses/<id>/delete`   | Delete an expense              |
| GET        | `/terms`, `/privacy`      | Legal pages                    |

## Running tests

```bash
pytest                      # run everything
pytest tests/test_delete_expense.py
pytest -k "test_name"       # run tests matching a name
```

## Notes

- `app.secret_key` is a hard-coded development value. Replace it before deploying anywhere.
- SQLite foreign keys are enabled on every connection through `PRAGMA foreign_keys = ON`.
