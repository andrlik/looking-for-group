#!/usr/bin/env bash
set -e

echo "First installing pyenv..."

curl https://pyenv.run | bash
export PATH=/home/ubuntu/.pyenv/bin:"$PATH"
eval "$(pyenv init  -)"
eval "$(pyenv virtualenv-init -)"
pyenv update
pyenv install 3.7.0
pyenv global 3.7.0
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

echo "Installing poetry for python3.7..."
# Install poetry for python3.7
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

exit 0
