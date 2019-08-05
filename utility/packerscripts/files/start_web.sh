#!/usr/bin/env bash

set -e

echo "Reloading env variables..."
source /opt/lfg/env
cd /opt/lfg/django
echo "Starting server..."
exec poetry run config/run.py
