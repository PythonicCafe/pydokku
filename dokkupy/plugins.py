import base64
import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .ssh import KEY_TYPES
from .utils import parse_bool, parse_timestamp

REGEXP_APP_METADATA = re.compile(r"App\s+([^:]+):\s*(.*)")
REGEXP_HEADER = re.compile("^=====> ", flags=re.MULTILINE)
REGEXP_ENSURE_DIR = re.compile("-----> Ensuring (.*) exists")
REGEXP_USER_GROUP = re.compile("Setting directory ownership to (.*):(.*)$")
REGEXP_SSH_PUBLIC_KEY = re.compile(f"ssh-({'|'.join(KEY_TYPES)}) AAAA[a-zA-Z0-9+/=]+( [^@]+@[^@]+)?")


@dataclass
class App:
    name: str
    created_at: datetime.datetime
    dir: Path
    locked: bool
    deploy_source: str = None
    deploy_source_metadata: str = None


class DokkuPlugin:
    name = None

    def __init__(self, dokku):
        self.dokku = dokku

    def _execute(self, command: str, params=None, stdin: str = None, check=True, sudo=False) -> str:
        cmd = ["dokku", f"{self.name}:{command}"]
        if params is not None:
            cmd.extend(params)
        return self.dokku._execute(cmd, stdin=stdin, check=check, sudo=sudo)


class AppsPlugin(DokkuPlugin):
    name = "apps"

    def list(self) -> List[str]:
        _, stdout, stderr = self._execute("report", check=False)
        if not stdout and "You haven't deployed any applications yet" in stderr:
            return []
        apps_infos = REGEXP_HEADER.split(stdout)[1:]
        result = []
        for app_info in apps_infos:
            lines = app_info.splitlines()
            keys_values = [REGEXP_APP_METADATA.findall(line.strip())[0] for line in lines[1:]]
            row = {
                "name": lines[0].split()[0],
                **{key.replace(" ", "_"): value or None for key, value in keys_values},
            }
            row["created_at"] = parse_timestamp(row["created_at"])
            row["dir"] = Path(row["dir"])
            row["locked"] = parse_bool(row["locked"])
            result.append(App(**row))
        return result

    def create(self, name: str) -> str:
        _, stdout, _ = self._execute("create", [name])
        return stdout

    def destroy(self, name: str) -> str:
        _, stdout, _ = self._execute("destroy", [name], stdin=name)
        return stdout

    def clone(self, old_name: str, new_name: str) -> str:
        _, stdout, _ = self._execute("clone", [old_name, new_name])
        return stdout

    def lock(self, name: str) -> str:
        _, stdout, _ = self._execute("lock", [name])
        return stdout

    def unlock(self, name: str) -> str:
        _, stdout, _ = self._execute("unlock", [name])
        return stdout

    def locked(self, name: str) -> str:
        _, stdout, stderr = self._execute("unlock", [name], check=False)
        return bool(stdout)

    def rename(self, old_name: str, new_name: str) -> str:
        _, stdout, _ = self._execute("rename", [old_name, new_name])
        return stdout


class ConfigPlugin(DokkuPlugin):
    name = "config"

    def get(self, app_name: str) -> str:
        # `dokku config <--global|app_name>` does not encode values, so we can't parse correctly if values has newlines
        # or other special chars. So we first get the keys and then read each key
        system = app_name is None
        _, stdout, _ = self._execute("export", ["--format=json", "--global" if system else app_name])
        return json.loads(stdout)

    def set_many(self, app_name: str, keys_values: dict, restart: bool = False) -> str:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        encoded_pairs = {
            key: base64.b64encode(str(value or "").encode("utf-8")).decode("ascii")
            for key, value in keys_values.items()
        }
        params = ["--encoded"]
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend([f"{key}={value}" for key, value in encoded_pairs.items()])
        _, stdout, _ = self._execute("set", params)
        return stdout

    def set(self, app_name: str, key: str, value: str, restart: bool = False) -> str:
        return self.set_many(app_name=app_name, keys_values={key: value}, restart=restart)

    def unset_many(self, app_name: str, keys: List[str], restart: bool = False) -> str:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend(keys)
        _, stdout, _ = self._execute("unset", params)
        return stdout

    def unset(self, app_name: str, key: str, restart: bool = False) -> str:
        return self.unset_many(app_name=app_name, keys=[key], restart=restart)

    def clear(self, app_name: str, restart: bool = False) -> str:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        _, stdout, _ = self._execute("clear", params)
        return stdout


@dataclass
class SSHKey:
    fingerprint: str
    name: str
    options: dict


class SSHKeysPlugin(DokkuPlugin):
    name = "ssh-keys"

    def list(self) -> List[dict]:
        _, stdout, stderr = self._execute("list", ["--format", "--json"], check=False)
        if "No public keys found" in stderr:
            return []
        result = []
        for item in json.loads(stdout):
            name, fingerprint = item.pop("name"), item.pop("fingerprint")
            result.append(SSHKey(name=name, fingerprint=fingerprint, options=item))
        return result

    def add(self, name: str, key: str | Path):
        """Add a SSH key to Dokku

        `key` can be the public key itself or the path to the public key file
        """
        key_content = None
        if isinstance(key, str):
            if REGEXP_SSH_PUBLIC_KEY.match(key):  # key is the actual string
                key_content = key
            else:
                key = Path(key)
        if isinstance(key, Path):
            with key.open() as fobj:
                key_content = fobj.read()
        if key_content is None:
            raise ValueError(f"Unknown key type: {repr(key)}")
        _, stdout, _ = self._execute("add", [name], stdin=key_content, sudo=True)
        return stdout

    def remove(self, name: str, is_fingerprint=False) -> str:
        _, stdout, _ = self._execute("remove", ["--fingerprint", name] if is_fingerprint else [name], sudo=True)
        return stdout


class StoragePlugin(DokkuPlugin):
    name = "storage"

    def list(self, app_name: str) -> List[dict]:
        _, stdout, _ = self._execute("list", [app_name, "--format", "json"], check=False)
        return json.loads(stdout)

    def ensure_directory(self, name, chown=None):
        chown_options = ("heroku", "herokuish", "packeto", "root")
        if chown is not None and chown not in chown_options:
            raise ValueError(f"Invalid value for chown: {repr(chown)} (expected: {', '.join(chown_options)})")
        params = [name]
        if chown is not None:
            params.extend(["--chown", chown])
        _, stdout, _ = self._execute("ensure-directory", params)
        lines = stdout.strip().splitlines()
        path = Path(REGEXP_ENSURE_DIR.findall(lines[0])[0])
        user, group = [int(item) for item in REGEXP_USER_GROUP.findall(lines[1])[0]]
        return path, (user, group)

    # TODO: implement storage:list <app> [--format text|json]                 List bind mounts for app's container(s) (host:container)
    # TODO: implement storage:report [<app>] [<flag>]                         Displays a checks report for one or more apps
    # TODO: implement storage:mount <app> <host-dir:container-dir>            Create a new bind mount
    # TODO: implement storage:unmount <app> <host-dir:container-dir>          Remove an existing bind mount
    # TODO: implement storage:ensure-directory [--chown option] <directory>   Creates a persistent storage directory in the recommended storage path


# TODO: implement checks:disable <app> [process-type(s)]   Disable zero-downtime deployment for all processes (or comma-separated process-type list) ***WARNING: this will cause downtime during deployments***
# TODO: implement checks:enable <app> [process-type(s)]    Enable zero-downtime deployment for all processes (or comma-separated process-type list)
# TODO: implement checks:report [<app>] [<flag>]           Displays a checks report for one or more apps
# TODO: implement checks:run <app> [process-type(s)]       Runs zero-downtime checks for all processes (or comma-separated process-type list)
# TODO: implement checks:skip <app> [process-type(s)]      Skip zero-downtime checks for all processes (or comma-separated process-type list)

# TODO: implement domains:add <app> <domain> [<domain> ...]       Add domains to app
# TODO: implement domains:add-global <domain> [<domain> ...]      Add global domain names
# TODO: implement domains:clear <app>                             Clear all domains for app
# TODO: implement domains:clear-global                            Clear global domain names
# TODO: implement domains:disable <app>                           Disable VHOST support
# TODO: implement domains:enable <app>                            Enable VHOST support
# TODO: implement domains:remove <app> <domain> [<domain> ...]    Remove domains from app
# TODO: implement domains:remove-global <domain> [<domain> ...]   Remove global domain names
# TODO: implement domains:report [<app>|--global] [<flag>]        Displays a domains report for one or more apps
# TODO: implement domains:set <app> <domain> [<domain> ...]       Set domains for app
# TODO: implement domains:set-global <domain> [<domain> ...]      Set global domain names

# TODO: implement nginx:access-logs <app> [-t]              Show the nginx access logs for an application (-t follows)
# TODO: implement nginx:error-logs <app> [-t]               Show the nginx error logs for an application (-t follows)
# TODO: implement nginx:report [<app>] [<flag>]             Displays an nginx report for one or more apps
# TODO: implement nginx:set <app> <property> (<value>)      Set or clear an nginx property for an app
# TODO: implement nginx:show-config <app>                   Display app nginx config
# TODO: implement nginx:start                               Starts the nginx server
# TODO: implement nginx:stop                                Stops the nginx server
# TODO: implement nginx:validate-config [<app>] [--clean]   Validates and optionally cleans up invalid nginx configurations

# TODO: implement ps:inspect <app>                                                   Displays a sanitized version of docker inspect for an app
# TODO: implement ps:rebuild [--parallel count] [--all|<app>]                        Rebuilds an app from source
# TODO: implement ps:report [<app>] [<flag>]                                         Displays a process report for one or more apps
# TODO: implement ps:restart [--parallel count] [--all|<app>] [<process-name>]       Restart an app
# TODO: implement ps:restore [<app>]                                                 Start previously running apps e.g. after reboot
# TODO: implement ps:scale [--skip-deploy] <app> <proc>=<count> [<proc>=<count>...]  Get/Set how many instances of a given process to run
# TODO: implement ps:set <app> <key> <value>                                         Set or clear a ps property for an app
# TODO: implement ps:start [--parallel count] [--all|<app>]                          Start an app
# TODO: implement ps:stop [--parallel count] [--all|<app>]                           Stop an app

# TODO: implement plugin:disable <name>                                                                               Disable an installed plugin (third-party only)
# TODO: implement plugin:enable <name>                                                                                Enable a previously disabled plugin
# TODO: implement plugin:install [--core|--git-url] [--committish branch|commit|commit] [--name custom-plugin-name]   Optionally download git-url (and pin to the specified branch/commit/tag) & run install trigger for active plugins (or only core ones)
# TODO: implement plugin:install-dependencies [--core]                                                                Run install-dependencies trigger for active plugins (or only core ones)
# TODO: implement plugin:list                                                                                         Print active plugins
# TODO: implement plugin:trigger <args...>                                                                            Trigger an arbitrary plugin hook
# TODO: implement plugin:uninstall <name>                                                                             Uninstall a plugin (third-party only)
# TODO: implement plugin:update [name [branch|commit|tag]]                                                            Optionally update named plugin from git (and pin to the specified branch/commit/tag) & run update trigger for active plugins

# TODO: implement redirect

# TODO: implement maintenance:enable <app>              Enable app maintenance mode
# TODO: implement maintenance:disable <app>             Disable app maintenance mode
# TODO: implement maintenance:report [<app>] [<flag>]   Displays an maintenance report for one or more apps
# TODO: implement maintenance:custom-page <app>         Imports a tarball from stdin; should contain at least maintenance.html

# TODO: implement letsencrypt:active <app>                     Verify if letsencrypt is active for an app
# TODO: implement letsencrypt:auto-renew [<app>]               Auto-renew app if renewal is necessary
# TODO: implement letsencrypt:cleanup <app>                    Remove stale certificate directories for app
# TODO: implement letsencrypt:cron-job [--add --remove]        Add or remove a cron job that periodically calls auto-renew.
# TODO: implement letsencrypt:disable <app>                    Disable letsencrypt for an app
# TODO: implement letsencrypt:enable <app>                     Enable or renew letsencrypt for an app
# TODO: implement letsencrypt:help                             Display letsencrypt help
# TODO: implement letsencrypt:list                             List letsencrypt-secured apps with certificate expiry times
# TODO: implement letsencrypt:revoke <app>                     Revoke letsencrypt certificate for app
# TODO: implement letsencrypt:set <app> <property> (<value>)   Set or clear a letsencrypt property for an app

# TODO: implement postgres:app-links <app>                                                        list all Postgres service links for a given app
# TODO: implement postgres:backup-auth <service> <aws-access-key-id> <aws-secret-access-key>...   set up authentication for backups on the Postgres service
# TODO: implement postgres:backup-deauth <service>                                                remove backup authentication for the Postgres service
# TODO: implement postgres:backup-schedule-cat <service>                                          cat the contents of the configured backup cronfile for the service
# TODO: implement postgres:backup-schedule <service> <schedule> <bucket-name>...                  schedule a backup of the Postgres service
# TODO: implement postgres:backup <service> <bucket-name> [-u|--use-iam-optional]                 create a backup of the Postgres service to an existing s3 bucket
# TODO: implement postgres:backup-set-encryption <service> <passphrase>                           set encryption for all future backups of Postgres service
# TODO: implement postgres:backup-set-public-key-encryption <service> <public-key-id>             set GPG Public Key encryption for all future backups of Postgres service
# TODO: implement postgres:backup-unschedule <service>                                            unschedule the backup of the Postgres service
# TODO: implement postgres:backup-unset-encryption <service>                                      unset encryption for future backups of the Postgres service
# TODO: implement postgres:backup-unset-public-key-encryption <service>                           unset GPG Public Key encryption for future backups of the Postgres service
# TODO: implement postgres:clone <service> <new-service> [--clone-flags...]                       create container <new-name> then copy data from <name> into <new-name>
# TODO: implement postgres:connect <service>                                                      connect to the service via the postgres connection tool
# TODO: implement postgres:create <service> [--create-flags...]                                   create a Postgres service
# TODO: implement postgres:destroy <service> [-f|--force]                                         delete the Postgres service/data/container if there are no links left
# TODO: implement postgres:enter <service>                                                        enter or run a command in a running Postgres service container
# TODO: implement postgres:exists <service>                                                       check if the Postgres service exists
# TODO: implement postgres:export <service>                                                       export a dump of the Postgres service database
# TODO: implement postgres:expose <service> <ports...>                                            expose a Postgres service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement postgres:import <service>                                                       import a dump into the Postgres service database
# TODO: implement postgres:info <service> [--single-info-flag]                                    print the service information
# TODO: implement postgres:linked <service> <app>                                                 check if the Postgres service is linked to an app
# TODO: implement postgres:link <service> <app> [--link-flags...]                                 link the Postgres service to the app
# TODO: implement postgres:links <service>                                                        list all apps linked to the Postgres service
# TODO: implement postgres:list                                                                   list all Postgres services
# TODO: implement postgres:logs <service> [-t|--tail] [<tail-num>]                                print the most recent log(s) for this service
# TODO: implement postgres:pause <service>                                                        pause a running Postgres service
# TODO: implement postgres:promote <service> <app>                                                promote service <service> as DATABASE_URL in <app>
# TODO: implement postgres:restart <service>                                                      graceful shutdown and restart of the Postgres service container
# TODO: implement postgres:set <service> <key> <value>                                            set or clear a property for a service
# TODO: implement postgres:start <service>                                                        start a previously stopped Postgres service
# TODO: implement postgres:stop <service>                                                         stop a running Postgres service
# TODO: implement postgres:unexpose <service>                                                     unexpose a previously exposed Postgres service
# TODO: implement postgres:unlink <service> <app>                                                 unlink the Postgres service from the app
# TODO: implement postgres:upgrade <service> [--upgrade-flags...]                                 upgrade service <service> to the specified versions

# TODO: implement mariadb:app-links <app>                                                        list all MariaDB service links for a given app
# TODO: implement mariadb:backup-auth <service> <aws-access-key-id> <aws-secret-access-key>...   set up authentication for backups on the MariaDB service
# TODO: implement mariadb:backup-deauth <service>                                                remove backup authentication for the MariaDB service
# TODO: implement mariadb:backup-schedule-cat <service>                                          cat the contents of the configured backup cronfile for the service
# TODO: implement mariadb:backup-schedule <service> <schedule> <bucket-name>...                  schedule a backup of the MariaDB service
# TODO: implement mariadb:backup <service> <bucket-name> [-u|--use-iam-optional]                 create a backup of the MariaDB service to an existing s3 bucket
# TODO: implement mariadb:backup-set-encryption <service> <passphrase>                           set encryption for all future backups of MariaDB service
# TODO: implement mariadb:backup-set-public-key-encryption <service> <public-key-id>             set GPG Public Key encryption for all future backups of MariaDB service
# TODO: implement mariadb:backup-unschedule <service>                                            unschedule the backup of the MariaDB service
# TODO: implement mariadb:backup-unset-encryption <service>                                      unset encryption for future backups of the MariaDB service
# TODO: implement mariadb:backup-unset-public-key-encryption <service>                           unset GPG Public Key encryption for future backups of the MariaDB service
# TODO: implement mariadb:clone <service> <new-service> [--clone-flags...]                       create container <new-name> then copy data from <name> into <new-name>
# TODO: implement mariadb:connect <service>                                                      connect to the service via the mariadb connection tool
# TODO: implement mariadb:create <service> [--create-flags...]                                   create a MariaDB service
# TODO: implement mariadb:destroy <service> [-f|--force]                                         delete the MariaDB service/data/container if there are no links left
# TODO: implement mariadb:enter <service>                                                        enter or run a command in a running MariaDB service container
# TODO: implement mariadb:exists <service>                                                       check if the MariaDB service exists
# TODO: implement mariadb:export <service>                                                       export a dump of the MariaDB service database
# TODO: implement mariadb:expose <service> <ports...>                                            expose a MariaDB service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement mariadb:import <service>                                                       import a dump into the MariaDB service database
# TODO: implement mariadb:info <service> [--single-info-flag]                                    print the service information
# TODO: implement mariadb:linked <service> <app>                                                 check if the MariaDB service is linked to an app
# TODO: implement mariadb:link <service> <app> [--link-flags...]                                 link the MariaDB service to the app
# TODO: implement mariadb:links <service>                                                        list all apps linked to the MariaDB service
# TODO: implement mariadb:list                                                                   list all MariaDB services
# TODO: implement mariadb:logs <service> [-t|--tail] [<tail-num>]                                print the most recent log(s) for this service
# TODO: implement mariadb:pause <service>                                                        pause a running MariaDB service
# TODO: implement mariadb:promote <service> <app>                                                promote service <service> as DATABASE_URL in <app>
# TODO: implement mariadb:restart <service>                                                      graceful shutdown and restart of the MariaDB service container
# TODO: implement mariadb:set <service> <key> <value>                                            set or clear a property for a service
# TODO: implement mariadb:start <service>                                                        start a previously stopped MariaDB service
# TODO: implement mariadb:stop <service>                                                         stop a running MariaDB service
# TODO: implement mariadb:unexpose <service>                                                     unexpose a previously exposed MariaDB service
# TODO: implement mariadb:unlink <service> <app>                                                 unlink the MariaDB service from the app
# TODO: implement mariadb:upgrade <service> [--upgrade-flags...]                                 upgrade service <service> to the specified versions

# TODO: implement redis:app-links <app>                                                        list all Redis service links for a given app
# TODO: implement redis:backup-auth <service> <aws-access-key-id> <aws-secret-access-key>...   set up authentication for backups on the Redis service
# TODO: implement redis:backup-deauth <service>                                                remove backup authentication for the Redis service
# TODO: implement redis:backup-schedule-cat <service>                                          cat the contents of the configured backup cronfile for the service
# TODO: implement redis:backup-schedule <service> <schedule> <bucket-name>...                  schedule a backup of the Redis service
# TODO: implement redis:backup <service> <bucket-name> [-u|--use-iam-optional]                 create a backup of the Redis service to an existing s3 bucket
# TODO: implement redis:backup-set-encryption <service> <passphrase>                           set encryption for all future backups of Redis service
# TODO: implement redis:backup-set-public-key-encryption <service> <public-key-id>             set GPG Public Key encryption for all future backups of Redis service
# TODO: implement redis:backup-unschedule <service>                                            unschedule the backup of the Redis service
# TODO: implement redis:backup-unset-encryption <service>                                      unset encryption for future backups of the Redis service
# TODO: implement redis:backup-unset-public-key-encryption <service>                           unset GPG Public Key encryption for future backups of the Redis service
# TODO: implement redis:clone <service> <new-service> [--clone-flags...]                       create container <new-name> then copy data from <name> into <new-name>
# TODO: implement redis:connect <service>                                                      connect to the service via the redis connection tool
# TODO: implement redis:create <service> [--create-flags...]                                   create a Redis service
# TODO: implement redis:destroy <service> [-f|--force]                                         delete the Redis service/data/container if there are no links left
# TODO: implement redis:enter <service>                                                        enter or run a command in a running Redis service container
# TODO: implement redis:exists <service>                                                       check if the Redis service exists
# TODO: implement redis:export <service>                                                       export a dump of the Redis service database
# TODO: implement redis:expose <service> <ports...>                                            expose a Redis service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement redis:import <service>                                                       import a dump into the Redis service database
# TODO: implement redis:info <service> [--single-info-flag]                                    print the service information
# TODO: implement redis:linked <service> <app>                                                 check if the Redis service is linked to an app
# TODO: implement redis:link <service> <app> [--link-flags...]                                 link the Redis service to the app
# TODO: implement redis:links <service>                                                        list all apps linked to the Redis service
# TODO: implement redis:list                                                                   list all Redis services
# TODO: implement redis:logs <service> [-t|--tail] [<tail-num>]                                print the most recent log(s) for this service
# TODO: implement redis:pause <service>                                                        pause a running Redis service
# TODO: implement redis:promote <service> <app>                                                promote service <service> as REDIS_URL in <app>
# TODO: implement redis:restart <service>                                                      graceful shutdown and restart of the Redis service container
# TODO: implement redis:set <service> <key> <value>                                            set or clear a property for a service
# TODO: implement redis:start <service>                                                        start a previously stopped Redis service
# TODO: implement redis:stop <service>                                                         stop a running Redis service
# TODO: implement redis:unexpose <service>                                                     unexpose a previously exposed Redis service
# TODO: implement redis:unlink <service> <app>                                                 unlink the Redis service from the app
# TODO: implement redis:upgrade <service> [--upgrade-flags...]                                 upgrade service <service> to the specified versions

# TODO: implement elasticsearch:app-links <app>                                              list all Elasticsearch service links for a given app
# TODO: implement elasticsearch:backup-set-public-key-encryption <service> <public-key-id>   set GPG Public Key encryption for all future backups of Elasticsearch service
# TODO: implement elasticsearch:backup-unset-public-key-encryption <service>                 unset GPG Public Key encryption for future backups of the Elasticsearch service
# TODO: implement elasticsearch:create <service> [--create-flags...]                         create a Elasticsearch service
# TODO: implement elasticsearch:destroy <service> [-f|--force]                               delete the Elasticsearch service/data/container if there are no links left
# TODO: implement elasticsearch:enter <service>                                              enter or run a command in a running Elasticsearch service container
# TODO: implement elasticsearch:exists <service>                                             check if the Elasticsearch service exists
# TODO: implement elasticsearch:expose <service> <ports...>                                  expose a Elasticsearch service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement elasticsearch:info <service> [--single-info-flag]                          print the service information
# TODO: implement elasticsearch:linked <service> <app>                                       check if the Elasticsearch service is linked to an app
# TODO: implement elasticsearch:link <service> <app> [--link-flags...]                       link the Elasticsearch service to the app
# TODO: implement elasticsearch:links <service>                                              list all apps linked to the Elasticsearch service
# TODO: implement elasticsearch:list                                                         list all Elasticsearch services
# TODO: implement elasticsearch:logs <service> [-t|--tail] [<tail-num>]                      print the most recent log(s) for this service
# TODO: implement elasticsearch:pause <service>                                              pause a running Elasticsearch service
# TODO: implement elasticsearch:promote <service> <app>                                      promote service <service> as ELASTICSEARCH_URL in <app>
# TODO: implement elasticsearch:restart <service>                                            graceful shutdown and restart of the Elasticsearch service container
# TODO: implement elasticsearch:set <service> <key> <value>                                  set or clear a property for a service
# TODO: implement elasticsearch:start <service>                                              start a previously stopped Elasticsearch service
# TODO: implement elasticsearch:stop <service>                                               stop a running Elasticsearch service
# TODO: implement elasticsearch:unexpose <service>                                           unexpose a previously exposed Elasticsearch service
# TODO: implement elasticsearch:unlink <service> <app>                                       unlink the Elasticsearch service from the app
# TODO: implement elasticsearch:upgrade <service> [--upgrade-flags...]                       upgrade service <service> to the specified versions
