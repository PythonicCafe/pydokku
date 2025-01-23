#!/bin/bash

set -e

function log() { echo; echo; echo "[$(date --iso=seconds)] $@"; }


versions="3.8 3.9 3.10 3.11 3.12 3.13"
log "Installing Python versions: $versions"
for version in $versions; do
  pyenv install "$version"
  pyenv virtualenv "$version" "py${version}"
  pyenv activate "py${version}"
  pip install -U pip
  pip install -r /home/debian/requirements-development.txt
  pyenv deactivate
done
