#!/usr/bin/env bash
# Render build: install, collect static files, migrate and seed the database.
# Runs on Render's free plan, which has no pre-deploy step.
set -o errexit

cd main_project
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_demo
