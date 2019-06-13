#!/bin/bash

set -xe

/opt/elasticbeanstalk/hooks/restartappserver/enact/99restartnginx.sh

# eventHelper.py --msg "Worker and web server restarted." --severity INFO
