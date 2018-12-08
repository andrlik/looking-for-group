#!/bin/bash

set -xe

/usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf status | grep django_q
if [[ $? ]]; then
  /usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf restart django_q
fi

eventHelper.py --msg "Worker server restarted." --severity INFO
