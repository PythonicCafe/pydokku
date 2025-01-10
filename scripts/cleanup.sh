#!/bin/bash

command -v dokku > /dev/null 2>&1 || exit 0

# apps
dokku apps:list | grep -v '=====> My Apps' | grep -E --color=no 'test-' | while read appName; do
	echo $appName | dokku apps:destroy $appName
done

# config
testVars=$(dokku config:show --global | grep -v '=====> global env vars' | egrep -E --color=no '^test_' | sed 's/:.*//')
if [[ ! -z $testVars ]]; then
	dokku config:unset --global $testVars
fi

# ssh-keys
dokku ssh-keys:list 2> /dev/null | grep -E --color=no 'NAME="test-' | sed 's/.*NAME="//; s/".*//' | while read keyName; do
	sudo dokku ssh-keys:remove $keyName
done

# storage
sudo bash -c 'rm -rf /var/lib/dokku/data/storage/test-*'

# domains
dokku domains:set-global dokku.me

# checks
dokku checks:set --global wait-to-retire 60

# git
sudo bash -c 'rm -f /home/dokku/.ssh/id_* /home/dokku/.ssh/known_hosts'

# proxy
dokku proxy:set --global nginx

# Remove all apps plugin properties to avoid a bug on Dokku that persists plugin properties even when the app is
# destroyed. More info: <https://github.com/dokku/dokku/issues/7443>
find /var/lib/dokku/config/*/ -name 'test-*' | sudo xargs rm -rf
