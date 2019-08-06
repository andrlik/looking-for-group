#!/usr/bin/env bash
set -e

# Configure nginx
echo "Adding healthd logs"
mkdir -p /var/log/nginx/healthd
chown -R www-data /var/log/nginx
chgrp -R www-data /var/log/nginx
echo "Clearing default sites from nginx config"
rm -rf /etc/nginx/sites-enabled/*
echo "Adding LFG site to sites enabled..."
ln -s /etc/nginx/sites-available/lfg.conf /etc/nginx/sites-enabled/lfg.conf
echo "Reloading Nginx"
service nginx reload

exit 0
