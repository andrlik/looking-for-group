#!/usr/bin/env bash

set -e

echo "Updating pythonpath..."
export PYTHONPATH=/opt/lfg/django:$PYTHONPATH
echo "Reloading env variables..."
. /opt/lfg/env
echo "Displaying env vars for debugging..."
env
echo "Starting server..."
make prodserver
