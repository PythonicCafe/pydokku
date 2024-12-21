#!/bin/bash

set -e

function log() { echo; echo; echo "[$(date --iso=seconds)] $@"; }

log "Installing Docker"
apt remove docker.io docker-doc docker-compose podman-docker containerd runc
apt update
apt install -y ca-certificates curl gnupg lsb-release python3 python3-pip
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

log "Installing Dokku plugins"
dokku plugin:install https://github.com/dokku/dokku-elasticsearch.git
dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
dokku plugin:install https://github.com/dokku/dokku-maintenance.git
dokku plugin:install https://github.com/dokku/dokku-mariadb.git
dokku plugin:install https://github.com/dokku/dokku-mysql.git
dokku plugin:install https://github.com/dokku/dokku-postgres.git
dokku plugin:install https://github.com/dokku/dokku-redirect.git
dokku plugin:install https://github.com/dokku/dokku-redis.git
dokku plugin:install-dependencies

log "Installing Python tools"
apt install -y python3-venv
sudo -u debian bash -c 'python3 -m venv /home/debian/venv'
sudo -u debian bash -c 'cd /home/debian && source venv/bin/activate && pip install ipython pytest'
