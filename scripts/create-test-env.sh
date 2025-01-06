#!/bin/bash
# Creates apps and set configurations for each plugin so we have an environment to easily test things on

# domains - part 1
dokku domains:set-global dokku.example.net

# apps
for appName in test-app-7 test-app-8 test-app-9; do
	echo "$appName" | dokku apps:destroy "$appName"
	dokku apps:create "$appName"
done

# checks
dokku checks:set test-app-8 wait-to-retire 30
dokku checks:disable test-app-9 web,worker
dokku checks:skip test-app-9 another-worker

# config
dokku config:set --no-restart test-app-8 a=123 b=456 c=789
dokku config:set --no-restart test-app-9 DEBUG=True

# domains - part 2
dokku domains:set test-app-9 app9.example.com
dokku domains:add test-app-9 app9.example.net
dokku domains:remove test-app-7 test-app-7.dokku.example.net

# ssh-keys
for keyNumber in 1 2 3; do
	keyFilename=$(mktemp)
	rm -f "$keyFilename"
	ssh-keygen -t ed25519 -f "$keyFilename" -N "" -q
	cat "${keyFilename}.pub" | sudo dokku ssh-keys:add "test-key-${keyNumber}"
	rm -rf "$keyFilename" "${keyFilename}.pub"
done

# storage
dokku storage:ensure-directory test-app-7-data
dokku storage:mount test-app-7 /var/lib/dokku/data/storage/test-app-7-data:/data
dokku storage:ensure-directory --chown heroku test-app-9-data
dokku storage:mount test-app-9 /var/lib/dokku/data/storage/test-app-9-data:/data
