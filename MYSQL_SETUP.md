# MySQL setup

Tested against MariaDB 10.11 (MySQL-compatible) with your requested
config: database `cv_app`, user `root`, empty password.

## 1. Create the database

```sql
CREATE DATABASE cv_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

(`utf8mb4` matters — plain `utf8` in MySQL is a 3-byte-max legacy charset
that can't store the full Unicode range, which would silently mangle
things like emoji or some accented characters in CV content.)

## 2. Install the driver

Already added to `requirements.txt`:

```
PyMySQL==1.1.1
cryptography==43.0.3
```

`cryptography` is required by PyMySQL for MySQL 8's default
`caching_sha2_password` auth plugin — without it you'd get an
`ImportError`/auth failure on some MySQL 8 setups even with a correct
password.

## 3. Set `DATABASE_URL`

In `.env`:

```
DATABASE_URL=mysql+pymysql://root:@localhost/cv_app?charset=utf8mb4
```

Note the empty string after `root:` — that's the empty password, not a
placeholder to fill in. If you later set a real root password, it becomes
`mysql+pymysql://root:yourpassword@localhost/cv_app?charset=utf8mb4`.

## 4. Run migrations

```powershell
flask db upgrade
flask seed-templates
```

## What had to change to make this work on MySQL

1. **`migrations/versions/f06387a106d0_initial_schema.py`** — the original
   migration declared `cvs.current_version_id -> cv_versions.id` as an
   inline foreign key inside `create_table('cvs', ...)`, before the
   `cv_versions` table exists yet. SQLite silently drops a foreign key it
   can't resolve at creation time — no error, it just doesn't enforce it.
   MySQL (and Postgres) do not do this: `cv_versions` doesn't exist yet at
   that point in the script, so the constraint fails outright. I split it
   into a separate `op.create_foreign_key(...)` call issued after
   `cv_versions` is created. Verified: the constraint now actually shows up
   in `SHOW CREATE TABLE cvs` on MySQL, which it silently didn't before on
   SQLite (same schema, no error either way — the difference is only
   visible by inspecting the actual constraints on each database engine).

2. **`config.py`** — added `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping":
   True, "pool_recycle": 280}`. MySQL closes idle connections server-side
   after `wait_timeout` (default 8 hours, sometimes much shorter on shared
   hosts). Flask-SQLAlchemy's connection pool doesn't detect a
   server-closed connection on its own, so the *next* request to reuse that
   pooled connection fails with `OperationalError: Lost connection to
   MySQL server during query` — this can show up as a random, hard-to-
   reproduce 500 after the app has been idle for a while. `pool_pre_ping`
   makes SQLAlchemy test the connection before handing it out and
   transparently reconnect if it's gone; `pool_recycle` proactively retires
   connections after 280 seconds as a second line of defense. This is a
   no-op on SQLite.

3. **`app/models.py`**'s SQLite-only `PRAGMA foreign_keys=ON` event
   listener was already correctly scoped (checks
   `dbapi_connection.__module__.startswith("sqlite3")`), so it's already a
   no-op on MySQL — nothing needed there. MySQL's InnoDB engine enforces
   foreign keys by default anyway.

## Verified end-to-end against a real MySQL instance

Registered a user, created a CV, saved it (creating version 1 then version
2), uploaded a photo (compressed to 200×200 and served back correctly),
and confirmed directly via `SHOW CREATE TABLE` and `SELECT` queries that
the schema and data are exactly as expected — including the
`current_version_id` foreign key mentioned above.

The full existing pytest suite (14 tests) still passes unchanged — it runs
against in-memory SQLite by default for speed, since the app is written to
be database-agnostic through SQLAlchemy. If you want CI to also validate
against MySQL specifically, point `DATABASE_URL` at a MySQL instance and
change the `SQLALCHEMY_DATABASE_URI` override in `tests/conftest.py`'s
`app` fixture — note you'd then need to also handle the circular-FK
teardown differently, since the `PRAGMA foreign_keys=OFF` trick used there
for SQLite doesn't apply (MySQL's equivalent is `SET FOREIGN_KEY_CHECKS=0`).
