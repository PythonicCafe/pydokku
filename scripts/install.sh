#!/bin/bash

set -e

function log() { echo; echo; echo "[$(date --iso=seconds)] $@"; }

log "Install packages to build Python (useful if using pyenv)"
apt update
apt install -y build-essential git libbz2-dev libffi-dev liblzma-dev libncurses-dev libreadline-dev libsqlite3-dev libssl-dev

log "Installing Docker"
apt remove docker.io docker-doc docker-compose podman-docker containerd runc
apt update
apt install -y byobu ca-certificates curl gnupg lsb-release python3 python3-pip
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
apt clean
docker run --rm hello-world

log "Installing Dokku"
wget -qO- https://packagecloud.io/dokku/dokku/gpgkey | tee /etc/apt/trusted.gpg.d/dokku.asc
echo "deb https://packagecloud.io/dokku/dokku/debian/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/dokku.list
apt update
echo "dokku dokku/vhost_enable boolean true" | debconf-set-selections
echo "dokku dokku/hostname string dokku.me" | debconf-set-selections
echo "dokku dokku/key_file string /root/.ssh/id_rsa.pub" | debconf-set-selections
echo "dokku dokku/skip_key_file boolean true" | debconf-set-selections
echo "dokku dokku/nginx_enable boolean true" | debconf-set-selections
apt install -y dokku
apt clean
dokku plugin:install-dependencies --core
adduser debian dokku
chown -R debian:debian /home/debian

log "Installing Python tools"
apt install -y python3-venv
sudo -u debian bash -c 'python3 -m venv /home/debian/venv'
sudo -u debian bash -c 'cd /home/debian && source venv/bin/activate && pip install -r /home/debian/requirements-development.txt'

sudo bash -c 'echo "host_shared /shared virtiofs defaults 0 0" >> /etc/fstab'
sudo systemctl daemon-reload
sudo mkdir /shared
sudo mount /shared

log "Installing pyenv"
BASHRC_PATH="/home/debian/.bashrc"
PYENV_PATH="/home/debian/.pyenv"
rm -rf "$PYENV_PATH"
sudo -u debian git clone https://github.com/pyenv/pyenv.git "$PYENV_PATH"
sudo -u debian git clone https://github.com/pyenv/pyenv-virtualenv.git "${PYENV_PATH}/plugins/pyenv-virtualenv"
sudo -u debian touch "$BASHRC_PATH"
if [[ $(grep PYENV "$BASHRC_PATH" | wc -l) = 0 ]]; then
  echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$BASHRC_PATH"
  echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> "$BASHRC_PATH"
  echo 'eval "$(pyenv init - bash)"' >> "$BASHRC_PATH"
fi
