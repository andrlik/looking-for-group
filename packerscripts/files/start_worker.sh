#!/usr/bin/env bash

set -e

echo "Updating python path..."
export PYTHONPATH=/opt/lfg/django:$PYTHONPATH

echo "Sourcing env variables..."
. /opt/lfg/env

echo "Displaying env vars for debugging..."
env

echo "Starting worker..."
make qcluster
