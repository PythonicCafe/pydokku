#!/bin/bash
# Creates apps and set configurations for each plugin so we have an environment to easily test things on

set -e

# domains - part 1
dokku domains:set-global dokku.example.net

# apps
for appName in test-app-5 test-app-6 test-app-7 test-app-8 test-app-9; do
	echo "$appName" | dokku apps:destroy "$appName" 2> /dev/null || echo
	dokku apps:create "$appName"
done

# checks
dokku checks:set test-app-8 wait-to-retire 30
dokku checks:disable test-app-9 web,worker
dokku checks:skip test-app-9 another-worker

# config
dokku config:set --global DOKKU_RM_CONTAINER=1  # don't keep `run` containers around
dokku config:set --no-restart test-app-8 a=123 b=456 c=789
dokku config:set --no-restart test-app-9 DEBUG=True

# domains - part 2
dokku domains:set test-app-9 app9.example.com
dokku domains:add test-app-9 app9.example.net
dokku domains:remove test-app-7 test-app-7.dokku.example.net

# ssh-keys
for keyNumber in 1 2 3; do
	keyName="test-key-${keyNumber}"
	keyFilename=$(mktemp)
	rm -f "$keyFilename"
	ssh-keygen -t ed25519 -f "$keyFilename" -N "" -q
	sudo dokku ssh-keys:remove "$keyName" 2> /dev/null || echo
	cat "${keyFilename}.pub" | sudo dokku ssh-keys:add "$keyName"
	rm -rf "$keyFilename" "${keyFilename}.pub"
done

# storage
dokku storage:ensure-directory test-app-7-data
dokku storage:mount test-app-7 /var/lib/dokku/data/storage/test-app-7-data:/data
dokku storage:ensure-directory --chown heroku test-app-9-data
dokku storage:mount test-app-9 /var/lib/dokku/data/storage/test-app-9-data:/data

# ps
dokku ps:scale test-app-9 web=2 worker=3

# git
dokku git:generate-deploy-key
dokku git:from-image test-app-8 nginx:1.27.3-alpine-perl
dokku git:set --global deploy-branch stable
dokku git:set test-app-7 deploy-branch develop
dokku git:set test-app-7 keep-git-dir false
dokku git:set test-app-7 source-image nginx:1.27.3-alpine-perl
dokku git:allow-host github.com
dokku git:auth github.com user8 pass8
dokku git:auth gitlab.com user9 pass9

# proxy
dokku proxy:set --global caddy
dokku proxy:set test-app-8 nginx
dokku proxy:disable test-app-7

# ports
dokku ports:set test-app-7 http:80:3000 https:443:3000
dokku ports:add test-app-9 http:8080:5000 https:8081:5000

# nginx
dokku nginx:set --global client-max-body-size 123456
dokku nginx:set --global error-log-path
dokku nginx:set test-app-8 hsts-max-age 84600
dokku nginx:set test-app-7 send-timeout 120s

# network
for network in $(seq 1 3); do
    dokku network:create "test-net-${network}"
done
dokku network:set --global initial-network test-net-1
dokku network:set test-app-6 bind-all-interfaces false
dokku network:set test-app-6 tld svc.cluster.local
dokku network:set test-app-7 attach-post-deploy test-net-2
dokku network:set test-app-7 static-web-listener 127.0.0.1:5000
dokku network:set test-app-8 attach-post-create test-net-2
dokku network:set test-app-9 attach-post-create test-net-2
dokku network:set test-app-9 bind-all-interfaces true
dokku network:set test-app-9 initial-network none
