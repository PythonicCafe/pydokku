# pydokku

pydokku is a Python library and command-line tool to interface with Dokku. It makes it pretty easy to get structured
data regarding a Dokku server and also to easily inspect and setup apps and its configurations. It supports interfacing
with a local Dokku or via SSH (using a multiplexed connection for speed). Dokku is an awesome project but has some
caveats in the user experience - pydokku can help improve it!

Goals:
- Create a well tested tool to interface/control Dokku (currently test coverage is ~85%)
- Fix some of the Dokku [annoying weaknesses](https://github.com/dokku/dokku/issues/7470#issuecomment-2629073346),
  [missing features](https://github.com/dokku/dokku/issues/1558), [lack of
  standards](https://github.com/dokku/dokku/issues/7454) when possible (no
  [footguns](https://github.com/dokku/dokku/issues/7438) allowed here)
- Provide a clean and more consistent data model (compared to Dokku's) whenever possible (see "Terminology and
  Compatibility")

> Note: it's not a current goal to support commands which outputs a huge ammount of data (like `postgres:export`) or
> requires a huge amount of data into the command's standard input (like `git:load-image`). We may work on that later.


## Python and Dokku versions

pydokku is developed mainly in Python 3.11 but may run smoothly in Python 3.8+ installations, so it'll be useful to
grab data about that old Dokku running on Ubuntu 20.04. :)

pydokku is being tested on the latest version of Dokku as of 2025-02-02 (0.35.15) but may work on older versions.  Some
support was added to help exporting data from old Dokku installations, like the ones before 0.31.0 where the `ports`
plugin didn't exist (the commands were `proxy:ports-*`) - even in those cases, the extracted data will be in a format
totally equivalent to newer Dokku installations, which makes migrations easier (use pydokku to export a JSON
representation of an old Dokku server and use that JSON with pydokku to apply those configurations in a new Dokku
installation).

> Note: some features may not be available for older Dokku versions, like complete network information on versions
> before 0.35.3 (if the user running cannot execute other commands than Dokku) and global port configuration (didn't
> exist before 0.31.0). The general recommendation is to upgrade Dokku as soon as possible, since maintaing code
> compatible with older/buggy versions is very costly.


## Usage

As a command-line tool:

```shell
pydokku export mydokku.json
# Will create the `mydokku.json` file with all information regarding this dokku installation.

pydokku export --app myapp mydokku-app.json
# Will create the `mydokku-app.json` file with all information regarding the app, including required plugins.

pydokku apply mydokku.json
# Will execute all specs from the JSON file (create apps, configure plugins etc.). The commands will be executed in a
# specific order to guarantee consistency between plugin requirements.
# Not sure about what the command above will execute? Run:

pydokku apply --print-only mydokku.json
# Will read the `mydokku.json` file, transform each specification in a list of Dokku commands and print the commands to
# stdout, without executing them.
```

As a Python library:

```python
from pydokku import Dokku

dokku = Dokku()

apps = dokku.apps.list()
print(f"Current apps: {', '.join(app.name for app in apps) if apps else '(none)'}")
# Current apps: (none)

dokku.apps.create("myapp1")
dokku.apps.create("myapp2")
apps = dokku.apps.list()
print(f"Current apps: {', '.join(app.name for app in apps) if apps else '(none)'}")
# Current apps: myapp1, myapp2

app = apps[0]
print(app)
# App(
#   name='myapp1',
#   path=PosixPath('/home/dokku/myapp1'),
#   locked=False,
#   created_at=datetime.datetime(2025, 1, 9, 14, 25, 1, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=75600), '-03')),
#   deploy_source=None,
#   deploy_source_metadata=None,
# )

dokku.config.clear("myapp2")
# '-----> Unsetting NO_VHOST\n'

dokku.config.set_many_dict("myapp2", {"key1": "val1", "key2": "val2"})
# '-----> Setting config vars\n       key1:  val1\n       key2:  val2\n'

dokku.ps.set_scale("myapp1", {"web": 2, "worker": 3})
# '-----> Scaling myapp1 processes: web=2 worker=3\n'

# Now let's create some storage for the apps
from pydokku.models import Storage
from pydokku.utils import human_readable_size

host_path, (user_id, group_id) = dokku.storage.ensure_directory("myapp1-storage", chown="heroku")
storage_1 = Storage(app_name="myapp1", host_path=host_path, container_path="/data", user_id=user_id, group_id=group_id)
host_path, (user_id, group_id) = dokku.storage.ensure_directory("myapp2-storage", chown="heroku")
storage_2 = Storage(app_name="myapp2", host_path=host_path, container_path="/data", user_id=user_id, group_id=group_id)
dokku.storage.mount(storage_1)
dokku.storage.mount(storage_2)

# With the storage mounted, let's create some files so then we can check how much each directory have
(storage_1.host_path / "myfile.txt").write_text("some content" * 100_000)
(storage_2.host_path / "myfile.txt").write_text("some content" * 1_000_000)
for app in dokku.apps.list():
    for storage in dokku.storage.list(app.name):
        size = dokku.storage.size(storage)  # Requires extra commands to be executed
        print(f"{storage.host_path} ({app.name}): {human_readable_size(size)}")
# /var/lib/dokku/data/storage/myapp1-storage (myapp1): 1.15 MB
# /var/lib/dokku/data/storage/myapp2-storage (myapp2): 11.45 MB

# Access other plugins via `dokku.<plugin_name>`
```

Currently implemented plugins:
- (core) `apps`
- (core) `checks`
- (core) `config`
- (core) `domains`
- (core) `git`
- (core) `network`
- (core) `nginx`
- (core) `plugin`
- (core) `ports`
- (core) `proxy`
- (core) `ps`
- (core) `ssh-keys`
- (core) `storage`
- (official) `maintenance`
- (official) `redirect`
- (official) `letsencrypt`

Plugins to be implemented soon (hopefully before 0.1.0):
- (core) `docker-options`
- (core) `logs`
- (core) `run`
- (official, service) `postgres`
- (official, service) `mariadb`
- (official, service) `mysql`
- (official, service) `redis`
- (official, service) `elasticsearch`
- (official, service) `rabbitmq`


## Terminology and Compatibility

- Each plugin has its own associated dataclasses, representing the objects managed by that plugin. These objects
  correspond to Dokku settings but do not directly map to the "rows" displayed in `dokku <plugin>:report|list`
  commands. In some plugins, a deliberate choice was made to represent the "global" object separately (e.g., in the
  `domains` plugin). In others, there may be multiple dataclasses, as they represent entirely different entities (e.g.,
  in the `git` plugin).
- All plugins have a `list()` method to execute the `:report` or `:list` Dokku-equivalent subcommand - so you always
  use one name for listing the objects and don't need to be confused about which is the correct name to use in which
  plugin. The only exception is `network`, which have both (the outputs are different).
- Because of the way Dokku works, if you don't have any application created you may not get the global values for the
  system in some plugins (like `nginx`). Dokku adds the global information in the middle of the app report, so you need
  at least one dummy app to have the global output.
- The command and attribute names are more or less the same as in Dokku, except for:
  - `system` is used instead of `global`, since `global` is a Python reserved keyword
  - `path` is used instead of `dir` to maintain consistency with Python standard library (`pathlib` module)
  - `git_reference` is used instead of `committish`, `tag`, `branch` and `commit`
  - Some standardization to make actions more clear, like:
    - `dokku.git.host_add` for executing `git:allow-host` (the command adds a host to the list of SSH known hosts for
      the Dokku user)
    - `dokku.git.auth_add` for executing `git:auth` (the command adds the host/user/password to the netrc
      authentication database)
- Use `app_name=None` for meaning `--global` or `--all`
- Commands that have the exact same behavior are merged together, like `domains:set` and `domains:set-global` (for
  "global", call `dokku.domains.set` with `app_name=None`)
- Commands that can have different behaviors depending on the parameters were split in two methods, like `checks:set`
  (both `dokku.checks.set` and `dokku.checks.unset` were implemented)
- Redundant or unnecessary commands (from the library's point of view) will not implemented, like
  `config:export`/`config:show` and `apps:exists`
- Extra features were add to address some of Dokku's weaknesses and enable `pydokku` to provide a comprehensive view of
  all Dokku-related settings (this helps exporting all settings from a server and apply to another), like:
  - `dokku.ssh_keys.list` will add the actual public key by reading the Dokku SSH authorized keys file (if the user has
    the permission to do so)
  - `dokku.storage.list` will add the storage permissions (created using `storage:ensure-directory --chown=xxx`) for
    each storage (if the user has the permission to do so)
  - `dokku.git.host_list` will list all known SSH hosts by reading the file (if the user has the permission to do so)
  - `dokku.git.auth_list` will list all authentication hosts/users/passwords added via `git:auth`
- Some features were not implemented, like the ones which require huge stdin/stdout traffic, like `git:load-image` and
  `maintenance:custom-page`.

The extra features require certain permissions to execute, as the information is not directly provided by any Dokku
command. In these cases, `pydokku` will need to run non-Dokku commands. There are six different scenarios you may run
`pydokku`, but only one of them will prevent these extra features from being executed:
- Executing `pydokku` on a local Dokku installation:
  - ✓ Using the `dokku` user
  - ✓ Using the `root` user
  - ✓ Using another user (requires sudo with no password)
- Running `pydokku` locally to control another host via SSH:
  - ✗ Using the `dokku` user (this user can't execute regular shell commands, only Dokku commands)
  - ✓ Using the `root` user
  - ✓ Using another user (requires sudo with no password)

> **WARNING**: if you export your Dokku settings using `pydokku` via SSH with the `dokku` user, you WON'T have all the
> Dokku settings required to reproduce the same environment on another server! Any information provided by the "extra
> features" will not be extracted.


## Next steps

After implementing a comprehensive set of plugins in order to be useful, the focus will be:

- Implement type-checking tools to enforce the declared types are correct (see `type-check` in `Makefile`)
- Implement "real" tests for all missing plugin commands
- Create an API to `object_ensure` method (similar to `object_create`, but won't raise an error if the object already
  exists). Or transform `apply`/`object_create` into "ensure".
- Define the concept of a "recipe", with variables for the context (similar to cookiecutter), the template itself and a
  "render" method. The CLI commands would be: `recipe-apply`, `recipe-render`, `recipe-ensure`.
- Replace `pathlib.Path` with `pathlib.PosixPath` when describing paths related to Dokku machine (if running remote on
  Windows, `Path` will not be `PosixPath`).
- Implement other official plugins:
  - `00_dokku-standard`
  - `20_events`
  - `app-json`
  - `builder-dockerfile`
  - `builder-herokuish`
  - `builder-lambda`
  - `builder-nixpacks`
  - `builder-null`
  - `builder-pack`
  - `builder`
  - `buildpacks`
  - `caddy-vhosts`
  - `certs`
  - `common`
  - `cron`
  - `enter`
  - `haproxy-vhosts`
  - `nginx-vhosts`
  - `openresty-vhosts`
  - `registry`
  - `repo`
  - `resource`
  - `scheduler-docker-local`
  - `scheduler-k3s`
  - `scheduler-null`
  - `scheduler`
  - `shell`
  - `trace`
  - `traefik-vhosts`
- Support for commands with long stdin/stdout (where we can't just store everything in RAM and would need a streaming
  approach)


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
