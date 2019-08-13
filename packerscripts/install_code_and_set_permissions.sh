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

echo "Reloading pyenv"

export PATH=/home/ubuntu/.pyenv/bin:"$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
echo "Install python requirements"


echo "Installing application requirements to pyenv site packages..."
# Install requirements for production use.

. /home/ubuntu/.poetry/env

export PIP_DISABLE_PIP_VERSION_CHECK=1
poetry config settings.virtualenvs.create false

. /opt/lfg/env

echo "Sourced env, now providing debug output"

env

echo "Installing all dependencies..."

make install_prod_deps

echo "Showing current python packages..."

pip list

echo "Prepping static files..."

make prep_static

cat<<EOF > /opt/lfg/django/config/run.py
from waitress import serve
from config import wsgi

open("/opt/lfg/app-initialized", "w").close()

serve(wsgi.application, unix_socket="/opt/lfg/nginx.socket")
EOF

echo "Codebase setup!"

exit 0
