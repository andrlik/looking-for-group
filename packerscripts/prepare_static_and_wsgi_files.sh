#!/usr/bin/bash

set -e

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
