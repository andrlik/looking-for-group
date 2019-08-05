#!/usr/bin/env bash
set -e

echo "First installing pyenv for www-data..."

sudo -u www-data curl https://pyenv.run | bash

sudo -u www-data echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile

chgrp -R www-data /home/ubuntu/.pyenv

sudo -u www-data /home/ubuntu/.pyenv/bin/pyenv update

sudo -u www-data /home/ubuntu/.pyenv/bin/pyenv install 3.7.0

sudo -u www-data /home/ubuntu/.pyenv/bin/pyenv global 3.7.0

echo "Installing poetry for python3.7..."
# Install poetry for python3.7
sudo -u www-data curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

exit 0
