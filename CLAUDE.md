# CLAUDE.md

Guidance for working in this repository.

## What this is

TigerMaps is a Django app that maps Princeton courses and buildings on an
interactive Leaflet map. It is a fork of ClassMaps, modernized for Django 4.2
and deployed on Render.

## Settings modules (important)

There are multiple settings modules; **always pass the right one**:

- `classmaps.settings` — production: PostgreSQL (`DATABASE_URL`) + Princeton CAS
  auth. Requires a `DATABASE_URL`; importing CAS views requires the CAS settings.
- `classmaps.settings_local` — local dev/tests: SQLite + Django's built-in auth.
  Uses `classmaps.urls_local` (replaces CAS login/logout with `auth_views`).
- `classmaps.settings_offline` — legacy; used historically for data scraping.

For anything local — running the server, migrations, or tests — use
`--settings=classmaps.settings_local` (or export `DJANGO_SETTINGS_MODULE`).

## Common commands

```bash
# Tests (use the classes label; bare `test` under namespace-package layout finds 0)
python manage.py test classes --settings=classmaps.settings_local

# System checks
python manage.py check --settings=classmaps.settings_local

# Guard against model/migration drift
python manage.py makemigrations --check --dry-run --settings=classmaps.settings_local

# Run the dev server
python manage.py runserver --settings=classmaps.settings_local

# Seed demo data (Princeton buildings + course sections) from scraping/*.json
python manage.py seed_demo --settings=classmaps.settings_local
```

## Data model

- `Building` — a campus building (name aliases joined with `/`, lat/lon, id).
- `Section` — one meeting of a course (listings, room, day, start/end time,
  enrollment). `listings` is stored as `/DEPT NUM[/DEPT NUM...]`; `__str__`
  strips the leading `/`.
- `User` — app-specific (keyed by CAS `netid`), **separate from Django's auth
  user**. Stores saved course/building ids in `JSONArrayField`s. Views map the
  authenticated `request.user.username` to this model's `netid`.

`JSONArrayField` (in `classes/models.py`) is a `TextField` that stores a JSON
list of strings. It is used uniformly on both SQLite and PostgreSQL — do not
reintroduce a PostgreSQL `ArrayField`, which would diverge from
`0001_initial` and break the SQLite path.

## Search logic

Lives in `classes/views.py` (`search_terms`, `search_day`, `search_time`,
`parse_terms`). It is regex-driven over building name aliases and course
listings; `search_day` uses `T(?!h)` so a Tuesday filter does not match a
Thursday-only class. This logic is covered by `classes/tests.py`.

## Public demo & access

Viewing is public: `index`, `search`, `query`, `enroll`, and the detail views
have no `@login_required`. Anonymous requests resolve to `netid = None` (see
`_current_netid` in `views.py`) and get no saved locations. Only `save`,
`remove`, and `saved_locations` require login (Princeton CAS in production).
Templates gate user-specific UI with `{% if netid %}` and show a "Log in with
Princeton" link otherwise.

`seed_demo` populates the demo from `scraping/*.json`; `build.sh` runs it on
every deploy (idempotent). The Princeton orange/black look is layered on via
`classes/static/classes/theme.css` (cosmetic `!important` overrides — keep map
layout/positioning out of it).

## Gotchas

- `classes/` and `classmaps/` need `__init__.py`; without them they work as
  implicit namespace packages at runtime but `unittest` test discovery breaks.
- `django-cas-ng` 5.x uses class-based views
  (`LoginView`/`LogoutView`/`CallbackView`), not the old function-based ones.
- Primary keys are `AutoField` (pinned in `0001_initial`); keep
  `DEFAULT_AUTO_FIELD`/`default_auto_field` as `AutoField` to avoid a spurious
  "alter id" migration.
