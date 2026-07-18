# CV Editor — Flask edition

Multi-user rewrite of the original PHP prototype. Each user has an account
and can own multiple CVs; every save creates a new immutable version so you
can browse and restore history; photos are automatically compressed to a
fixed square size on upload.

This implements **Phase 1 (Foundation) + Phase 2 (Versioning) + the photo
pipeline from Phase 4** of `plan.md`. See "What's not built yet" below for
what's intentionally deferred.

## Stack

Python 3.11+, Flask, SQLAlchemy + Flask-Migrate (Alembic), Flask-Login,
Flask-WTF (CSRF), Argon2 password hashing, Pillow for image processing,
Jinja2 templates. SQLite for now — see `plan.md` §3 for the Postgres
cutover path (the code is already written to make that a config change,
not a rewrite).

## Setup

```bash
cd cv-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit SECRET_KEY at minimum
export FLASK_APP=wsgi.py

flask db upgrade          # create instance/app.db and run migrations
flask seed-templates      # populate the templates table

flask run --port 5000
```

Open `http://localhost:5000`, register an account, and create your first
CV.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

11 tests cover: registration/login, duplicate-email rejection, wrong
password, login-required redirects, CV creation seeding version 1,
save-creates-new-version (old version untouched), restore-appends-a-new-
version (never a destructive rollback), cross-user access returning 404,
and preview rendering (including HTML-escaping of injected content).

## Project layout

```
cv-app/
├── app/
│   ├── __init__.py            # app factory
│   ├── extensions.py          # db, migrate, login_manager, csrf
│   ├── models.py              # User, Template, CV, CVVersion, Photo
│   ├── cv_schema.py           # blank_cv_data() / normalize_cv_data()
│   ├── auth/                  # register/login/logout
│   ├── cvs/                   # list/create/edit/save/versions/restore/photo
│   ├── main/                  # landing route
│   ├── services/
│   │   ├── cv_renderer.py     # **bold**/[fa:..] inline markup -> Jinja filter
│   │   └── photo_service.py   # validate + compress/resize + save photo
│   ├── templates/
│   │   ├── base.html, auth/, cvs/
│   │   └── cv_templates/classic_sidebar/layout.html.jinja
│   └── static/
│       ├── app.css, editor.css, editor.js
│       └── cv_templates/classic_sidebar/style.css
├── migrations/                 # Alembic
├── scripts/seed_templates.py
├── tests/
├── instance/
│   ├── app.db
│   └── storage/photos/<user_id>/<uuid>.jpg
├── config.py
└── wsgi.py
```

## What's implemented

- **Accounts**: register/login/logout (Flask-Login + Argon2id), CSRF on
  every state-changing request.
- **Multiple CVs per user**, each independently editable, listable, and
  deletable (soft delete).
- **Versioning**: every "Enregistrer" click inserts a new `cv_versions`
  row and moves `cvs.current_version_id` forward — nothing is ever
  overwritten. A version-history page lets you preview or restore any past
  version; restoring appends a new version rather than rolling back
  (`/cvs/<id>/versions`).
- **Templates**: presentation is decoupled from data — `classic_sidebar` is
  the only built-in template so far (a direct port of the PHP prototype's
  layout/CSS), but the `templates` DB table + `/cvs/<id>/view?template=`
  route are already wired for adding more (see plan.md §4 / Phase 3).
- **Photo upload**: 1 MB upload cap, real format sniffing via Pillow (not
  trusted from the client), EXIF-rotation-aware, cropped to a centered
  square, resized to **200×200** by default (120×120 supported via the
  `variant` form field), re-encoded as JPEG q82, and served through an
  access-controlled route (`/cvs/photos/<id>`, 404s for non-owners).
- **A4 print/export**: `/cvs/<id>/view` is a chrome-free, print-ready page
  (same approach as the PHP prototype's `preview.php`).

## What's not built yet

Deferred on purpose, tracked in `plan.md`'s phased roadmap:

- **PostgreSQL cutover** (Phase 5) — the JSON columns, Alembic migrations,
  and `PRAGMA foreign_keys` handling are already written so this should be
  a config change + the data-migration script, not a rewrite. That script
  itself (`scripts/migrate_sqlite_to_postgres.py`) hasn't been written yet.
- **Additional templates** (`minimal`, `two_column_timeline`) — the
  contract (`cv` dict shape, `cv_inline`/`contact_icon_class`/
  `link_icon_class` filters) is established; only `classic_sidebar` has
  been built so far.
- **Autosave** — saves are currently explicit-only (matches the PHP
  prototype's UX). The `cv_versions.is_autosave` column exists for this.
- **Rate limiting** on `/auth/login` and `/auth/register` (Flask-Limiter) —
  not wired in yet.
- **Orphaned-photo cleanup job** — uploading a new photo doesn't delete the
  old file from disk (intentionally, since old versions may still reference
  it), but nothing prunes genuinely orphaned files yet.
- **Diff view between two versions** — the version list shows metadata and
  lets you preview/restore, but doesn't yet show what actually changed
  between two versions.

## Security notes

`template_slug` (from query string or POST body) is always resolved
through `_resolve_template_slug()` in `app/cvs/routes.py`, which checks it
against the `templates` table (`is_active=True`) before it's ever used to
build a `render_template()` path — falling back to the CV's default
template, then to any active template, if the requested slug doesn't
exist. This closes off arbitrary template-path lookups from user input.
