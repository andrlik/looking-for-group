#!/usr/bin/env bash

set -e

echo "Loading pyenv for user www-data"
export PATH=/home/ubuntu/.pyenv/bin:"$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
. /home/ubuntu/.poetry/env
echo "Reloading env variables..."
. /opt/lfg/env
cd /opt/lfg/django
echo "Starting server..."
exec python config/run.py
