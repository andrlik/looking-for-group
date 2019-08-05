#!/usr/bin/env bash

set -e

echo "Sourcing env variables..."
source /opt/lfg/env

echo "Starting worker..."
cd /opt/lfg/django
exec python3.7 manage.py qcluster
