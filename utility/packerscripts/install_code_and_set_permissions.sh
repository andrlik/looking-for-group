#!/usr/bin/env bash
set -e

cd /opt/lfg/django

. /opt/lfg/env

# echo "Setting code base version to use..."

# CHECKOUT_TARGET=""

# if [[ -z "${LFG_TAG}" ]]; then
#     echo "No target tag specified... falling back to master. Please let this NOT be a production release!"
#     CHECKOUT_TARGET="master" # Falling back to using master: PLEASE DON'T DO THIS IN PRODUCTION!!!
# else
#     echo "Using ${LFG_TAG} as deployment target..."
#     CHECKOUT_TARGET="${LFG_TAG}"
# fi

# git checkout "${CHECKOUT_TARGET}"

echo "Install python requirements"


echo "Installing application requirements to virtualenv..."
# Install requirements for production use.

. /home/ubuntu/.poetry/env

export PIP_DISABLE_PIP_VERSION_CHECK=1
poetry config settings.virtualenvs.create false
poetry install --no-dev

echo "All python dependencies are now installed. Showing current package list:"

pip list

echo "Installing node dependencies..."

exec npm install

echo "Prune out dev..."

exec npm prune --production

echo "Running collect static"

poetry run ./manage.py collectstatic --noinput

poetry run ./manage.py compress --force

poetry run ./manage.py collectstatic --noinput

echo "Codebase setup!"
