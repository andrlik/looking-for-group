#!/bin/bash

set -xe

/usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf status | grep django_q
if [[ $? ]]; then
  /usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf restart django_q
fi

/usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf status | grep django | grep -v django_q
if [[ $? ]]; then
    /usr/local/bin/supervisorctl -c /opt/python/etc/supervisor.conf restart django
fi

eventHelper.py --msg "Worker and web server restarted." --severity INFO
