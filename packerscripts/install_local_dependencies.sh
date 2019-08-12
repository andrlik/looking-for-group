#!/usr/bin/env bash

set -e

cd /opt/lfg/django

echo "Installing node dependencies..."

exec npm install

echo "Prune out dev..."

exec npm prune --production

echo "Running collect static"

poetry run ./manage.py collectstatic --noinput

poetry run ./manage.py compress --force

poetry run ./manage.py collectstatic --noinput

echo "Codebase setup!"
