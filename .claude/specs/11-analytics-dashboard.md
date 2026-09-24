# Spec: Analytics Dashboard

## Overview
The "Analytics" link in the navbar currently opens a static "Coming Soon" placeholder (`templates/analytics.html`). This step replaces it with a real expense dashboard for the logged-in user, focused on where their money goes: a donut chart of spending by category, with the total in the centre, plus a legend showing each category's amount and share. Summary cards (total spent, number of transactions, top category) sit above the chart. The page reuses the existing query helpers and category colour tokens, so no new SQL or DB changes are needed, and it is drawn with inline SVG and CSS only (no chart libraries).

## Depends on
- Step 01 — Database setup (`expenses` table)
- Step 03 — Login and Logout (`session["user_id"]`)
- Step 05 — Backend routes for profile page (`get_summary_stats()`, `get_category_breakdown()` in `database/queries.py`)

## Routes
- `GET /analytics` — render the analytics dashboard for the current user — logged-in (redirects to `/login` otherwise). The route already exists as a placeholder; upgrade it to pass data to the template.

## Database changes
No database changes. Reuses:
- `get_summary_stats(user_id)` → `{total, count, top_category}`
- `get_category_breakdown(user_id)` → list of `{name, amount, percent}` sorted by amount DESC, percents summing to 100 (empty list when there are no expenses)

## Templates
- **Create:** none
- **Modify:** `templates/analytics.html`
  - Remove the "Coming Soon" markup entirely
  - Load `css/profile.css` (for the category colour tokens, card, stat and bar styles) and `css/analytics.css`
  - Page header: "Analytics" title, short subtitle, "+ Add Expense" button (`url_for('add_expense')`)
  - Three stat cards: Total Spent, Transactions, Top Category
  - "Spending by Category" section with:
    - An inline SVG donut: one `<circle>` segment per category using `stroke-dasharray` / `stroke-dashoffset` on a circle of circumference 100, starting at 12 o'clock, coloured by category via a `donut-seg--<category>` class
    - Total spent shown in the centre of the donut
    - A legend listing each category: colour swatch, name, amount (₹) and percent, plus a horizontal bar (reusing `.cat-bar` / `.cat-bar--<category>`)
  - Empty state when the user has no expenses: message plus a link to add an expense (no SVG rendered)

## Files to change
- `app.py` — `analytics()` passes `stats=get_summary_stats(uid)` and `categories=get_category_breakdown(uid)`
- `templates/analytics.html` — replace placeholder with the dashboard
- `static/css/analytics.css` — replace the "Coming Soon" styles with dashboard layout and donut styles

## Files to create
- `tests/test_11_analytics_dashboard.py` — pytest coverage for the definition of done

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values (category colours come from the `--cat-*` tokens in `profile.css`)
- All templates extend `base.html`
- No JavaScript chart libraries — the chart is inline SVG + CSS; vanilla JS only if needed at all
- No inline `<style>` tags; the only inline `style=` allowed is the data-driven bar width, matching `profile.html`
- Route stays thin: fetch data, render template — no DB logic in `app.py`
- `url_for()` for every internal link

## Definition of done
- [ ] Visiting `/analytics` while logged out redirects to `/login`
- [ ] Visiting `/analytics` while logged in returns 200 and no longer shows "Coming Soon"
- [ ] The page shows Total Spent, Transactions and Top Category matching the user's expenses
- [ ] The donut renders one segment per category the user has spent in, and the segment lengths add up to 100
- [ ] The legend lists every category with its amount and percent, largest first
- [ ] The total is shown in the centre of the donut
- [ ] Only the logged-in user's expenses are counted — another user's data never appears
- [ ] A user with no expenses sees an empty-state message with a link to add an expense, and no donut
- [ ] The "Analytics" navbar link is highlighted as active on this page
- [ ] `pytest` passes, including `tests/test_11_analytics_dashboard.py`
