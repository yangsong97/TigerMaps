#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Populate the public demo with Princeton building/course data.
# seed_demo is idempotent: it is a no-op once data exists, so this is safe
# to run on every deploy.
python manage.py seed_demo
