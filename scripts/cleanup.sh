#!/bin/bash

command -v dokku > /dev/null 2>&1 || exit 0

function log() { echo; echo; echo "[$(date --iso=seconds)] Cleaning: $@"; }

OLD_DOKKU=false
if dpkg --compare-versions $(dokku version | sed 's/dokku version //') lt 0.31.0; then
	OLD_DOKKU=true
fi

# First, plugins that don't require any `apps`

log "plugin"
for plugin in elasticsearch letsencrypt maintenance mariadb mysql postgres rabbitmq redirect redis; do
	sudo dokku plugin:uninstall "$plugin" 2> /dev/null || echo
done

log "ssh-keys"
dokku ssh-keys:list 2> /dev/null | grep -E --color=no 'NAME="test-' | sed 's/.*NAME="//; s/".*//' | while read keyName; do
	sudo dokku ssh-keys:remove $keyName
done

log "apps"
dokku apps:list | grep -v '=====> My Apps' | grep -E --color=no 'test-' | while read appName; do
	echo $appName | dokku apps:destroy $appName
done


# Then, plugins that require `apps`

log "config"
testVars=$(dokku config:show --global | grep -v '=====> global env vars' | egrep -E --color=no '^test_' | sed 's/:.*//')
if [[ ! -z $testVars ]]; then
	dokku config:unset --global $testVars
fi

log "storage"
sudo bash -c 'rm -rf /var/lib/dokku/data/storage/test-*'

log "domains"
dokku domains:set-global dokku.me

log "checks"
dokku checks:set --global wait-to-retire 60

log "git"
dokku git:set --global deploy-branch master
sudo bash -c 'rm -f /home/dokku/.ssh/id_* /home/dokku/.ssh/known_hosts'

log "proxy"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku proxy:set --global nginx
fi

log "nginx"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku nginx:set --global access-log-format
	dokku nginx:set --global access-log-path
	dokku nginx:set --global bind-address-ipv4
	dokku nginx:set --global bind-address-ipv6
	dokku nginx:set --global client-body-timeout
	dokku nginx:set --global client-header-timeout
	dokku nginx:set --global client-max-body-size
	dokku nginx:set --global disable-custom-config
	dokku nginx:set --global error-log-path
	dokku nginx:set --global hsts-include-subdomains
	dokku nginx:set --global hsts-max-age
	dokku nginx:set --global hsts-preload
	dokku nginx:set --global keepalive-timeout
	dokku nginx:set --global lingering-timeout
	dokku nginx:set --global proxy-buffer-size
	dokku nginx:set --global proxy-buffering
	dokku nginx:set --global proxy-buffers
	dokku nginx:set --global proxy-busy-buffers-size
	dokku nginx:set --global proxy-connect-timeout
	dokku nginx:set --global proxy-read-timeout
	dokku nginx:set --global proxy-send-timeout
	dokku nginx:set --global send-timeout
	dokku nginx:set --global underscore-in-headers
	dokku nginx:set --global x-forwarded-for-value
	dokku nginx:set --global x-forwarded-port-value
	dokku nginx:set --global x-forwarded-proto-value
	dokku nginx:set --global x-forwarded-ssl
fi
dokku nginx:set --global hsts
dokku nginx:set --global nginx-conf-sigil-path

log "network"
dokku --quiet network:list | grep -E --color=no '^test-' | while read network; do
	echo $network | dokku network:destroy $network
done
dokku network:set --global initial-network
dokku network:set --global bind-all-interfaces false
dokku network:set --global tld
dokku network:set --global attach-post-deploy
dokku network:set --global attach-post-create

log "letsencrypt"
if [[ "$OLD_DOKKU" == "false" ]]; then
	dokku letsencrypt:set --global email
fi

log "plugin properties"
# Remove all apps plugin properties to avoid a bug on Dokku that persists plugin properties even when the app is
# destroyed. More info: <https://github.com/dokku/dokku/issues/7443>
find /var/lib/dokku/config/*/ -name 'test-*' | sudo xargs rm -rf
