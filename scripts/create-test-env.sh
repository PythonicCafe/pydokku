#!/bin/bash
# Creates apps and set configurations for each plugin so we have an environment to easily test things on

set -e

function log() { echo; echo; echo "[$(date --iso=seconds)] Creating: $@"; }

OLD_DOKKU=false
if dpkg --compare-versions $(dokku version | sed 's/dokku version //') lt 0.31.0; then
	OLD_DOKKU=true
fi

log "domains - part 1"
dokku domains:set-global dokku.example.net

log "apps"
for appName in test-app-5 test-app-6 test-app-7 test-app-8 test-app-9; do
	echo "$appName" | dokku apps:destroy "$appName" 2> /dev/null || echo
	dokku apps:create "$appName"
done

log "checks"
dokku checks:set test-app-8 wait-to-retire 30
dokku checks:disable test-app-9 web,worker
dokku checks:skip test-app-9 another-worker

log "config"
dokku config:set --global DOKKU_RM_CONTAINER=1  # don't keep `run` containers around
dokku config:set --no-restart test-app-8 a=123 b=456 c=789
dokku config:set --no-restart test-app-9 DEBUG=True

log "domains - part 2"
dokku domains:set test-app-9 app9.example.com
dokku domains:add test-app-9 app9.example.net
dokku domains:remove test-app-7 test-app-7.dokku.example.net

log "ssh-keys"
for keyNumber in 1 2 3; do
	keyName="test-key-${keyNumber}"
	keyFilename=$(mktemp)
	rm -f "$keyFilename"
	ssh-keygen -t ed25519 -f "$keyFilename" -N "" -q
	sudo dokku ssh-keys:remove "$keyName" 2> /dev/null || echo
	cat "${keyFilename}.pub" | sudo dokku ssh-keys:add "$keyName"
	rm -rf "$keyFilename" "${keyFilename}.pub"
done

log "storage"
dokku storage:ensure-directory test-app-7-data
dokku storage:mount test-app-7 /var/lib/dokku/data/storage/test-app-7-data:/data
dokku storage:ensure-directory --chown heroku test-app-9-data
dokku storage:mount test-app-9 /var/lib/dokku/data/storage/test-app-9-data:/data

log "ps"
dokku ps:scale test-app-9 web=2 worker=3

log "git"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku git:generate-deploy-key
fi
dokku git:allow-host github.com
dokku git:auth github.com user8 pass8
dokku git:auth gitlab.com user9 pass9
dokku git:set --global deploy-branch stable
dokku git:set test-app-7 deploy-branch develop
dokku git:set test-app-7 keep-git-dir false
dokku git:set test-app-7 source-image nginx:1.27.3-alpine-perl
dokku git:from-image test-app-8 nginx:1.27.3-alpine-perl

log "proxy"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku proxy:set --global caddy
fi
dokku proxy:set test-app-8 nginx
dokku proxy:disable test-app-7

log "ports"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku ports:set test-app-7 http:80:3000 https:443:3000
	dokku ports:add test-app-9 http:8080:5000 https:8081:5000
else
	dokku proxy:ports-set test-app-7 http:80:3000 https:443:3000
	dokku proxy:ports-add test-app-9 http:8080:5000 https:8081:5000
fi

log "nginx"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku nginx:set --global client-max-body-size 123456
	dokku nginx:set --global error-log-path
	dokku nginx:set test-app-7 send-timeout 120s
fi
dokku nginx:set test-app-8 hsts-max-age 84600

log "network"
for network in $(seq 1 3); do
    dokku network:create "test-net-${network}"
done
dokku network:set --global attach-post-deploy test-net-1
dokku network:set test-app-6 bind-all-interfaces false
dokku network:set test-app-6 tld svc.cluster.local
dokku network:set test-app-7 attach-post-deploy test-net-2
dokku network:set test-app-7 static-web-listener 127.0.0.1:5000
dokku network:set test-app-8 attach-post-create test-net-2
dokku network:set test-app-9 attach-post-create test-net-2
dokku network:set test-app-9 bind-all-interfaces true
dokku network:set test-app-9 initial-network none

log "plugin"
TEMP_DIR="/var/lib/dokku/tmp"
sudo mkdir -p "$TEMP_DIR"
for plugin in elasticsearch letsencrypt maintenance mariadb mysql postgres rabbitmq redirect redis; do
	localRepoPath="${TEMP_DIR}/dokku-copy-${plugin}"
	if [[ ! -e "$localRepoPath" ]]; then
		sudo git clone "https://github.com/dokku/dokku-${plugin}.git" "$localRepoPath"
	fi
	sudo dokku plugin:install "file://${localRepoPath}/.git" --name "$plugin"
done
sudo dokku plugin:disable elasticsearch 2> /dev/null || echo

log "redirect"
dokku redirect:set test-app-8 old.example.net new.example.net
dokku redirect:set test-app-9 older.example.net new.example.net 302

log "maintenance"
dokku maintenance:enable test-app-7
dokku maintenance:disable test-app-8
# A custom page is currently not extracted by pydokku, but this was added so in the future we may explore this.
echo '<html><head><title>Under maintenance</title></head><body><p>This website is under maintenance.</p></body></html>' > maintenance.html
tar -cf maintenance.tar maintenance.html
cat maintenance.tar | dokku maintenance:custom-page test-app-7
rm maintenance.tar maintenance.html

log "letsencrypt"
dokku letsencrypt:set --global email infra@example.net
