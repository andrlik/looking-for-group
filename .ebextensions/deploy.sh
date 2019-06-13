set -e

SCRIPT_PATH=`dirname $0`

source $SCRIPT_PATH/utils.sh

if is_leader; then
  echo "Start leader deploy"
else
  echo "Start non-leader deploy"
fi

copy_ext $SCRIPT_PATH/files/django.conf /opt/python/etc/django.conf 0755 root root
copy_ext $SCRIPT_PATH/files/djangoq.conf /opt/python/etc/djangoq.conf 0755 root root
copy_ext $SCRIPT_PATH/files/launch_worker /opt/python/bin/launch_worker 0755 root root

copy_ext $SCRIPT_PATH/files/99_restart_services.sh /opt/elasticbeanstalk/hooks/appdeploy/enact/99_restart_services.sh 0755 root root
copy_ext $SCRIPT_PATH/files/99_restart_services.sh /opt/elasticbeanstalk/hooks/configdeploy/enact/99_restart_services.sh 0755 root root
copy_ext $SCRIPT_PATH/files/99_restart_services.sh /opt/elasticbeanstalk/hooks/restartappserver/enact/99_restart_services.sh 0755 root root


script_add_line /opt/python/etc/supervisord.conf "include" "[include]"
script_add_line /opt/python/etc/supervisord.conf "djangoq.conf" "files=djangoq.conf"
#script_add_line /opt/python/etc/supervisord.conf "include" "[include]"
#script_add_line /opt/python/etc/supervisord.conf "django.conf" "files=django.conf"

supervisorctl -c /opt/python/etc/supervisord.conf reread

supervisorctl -c /opt/python/etc/supervisord.conf update

supervisorctl -c /opt/python/etc/supervisord.conf restart django_q
