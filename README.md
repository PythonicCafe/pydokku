# pydokku

pydokku is a Python library and command-line tool to interface with Dokku. It makes it pretty easy to get structured
data regarding a Dokku server and also to easily setup apps and its configurations. It supports interfacing with a
local Dokku command or via SSH (using a multiplexed connection for speed).

Goals:
- Create a well tested tool to interface/control Dokku
- Fix some of the Dokku weaknesses/missing features when possible
- Have a cleaner interface and better data model then Dokku by:
  - Creating a dataclass for each plugin, representing all the information that plugin stores
  - Avoiding implementing redundant commands from the library's point of view (like `config:export` and `config:show`)

It's not a current goal to support commands which outputs a huge ammount of data (like `postgres:export`) or requires a
huge amount of data into the command's standard input (like `git:load-image`).

## Usage

As a command-line tool:

```shell
pydokku dump mydokku.json
# Will create the `mydokku.json` file with all information regarding this dokku installation

pydokku apply mydokku.json
# Will execute all specs from the JSON file (create apps, configure plugins etc.)
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

# Access other plugins via `dokku.<plugin_name>`
```

Currently implemented plugins:
- (core) `apps`
- (core) `checks`
- (core) `config`
- (core) `domains`
- (core) `git`
- (core) `ps`
- (core) `ssh-keys`
- (core) `storage`
- (core) `proxy`

Plugins to be implemented soon:
- (core) `ports`
- (core) `nginx`
- (core) `network`
- (core) `plugin`
- (official) `redirect`
- (official) `maintenance`
- (official) `letsencrypt`
- (official, service) `postgres`
- (official, service) `mariadb`
- (official, service) `mysql`
- (official, service) `redis`
- (official, service) `elasticsearch`
- (official, service) `rabbitmq`


## Next steps

After implementing a comprehensive set of plugins in order to be useful, the focus will be:

- Implement type-checking tools to enforce the declared types are correct
- Implement "real" tests for all missing plugin commands
- List all data that only will be exported if running locally or via SSH with an user different of `dokku`
- Create an API to `object_ensure` method (similar to `object_create`, but won't raise an error if the object already
  exists)
- Define the concept of a "recipe", with variables for the context (similar to cookiecutter), the template itself and a
  "render" method. The CLI commands would be: `recipe-load`, `recipe-render`, `recipe-ensure`.
- May rename CLI's `load` to `execute`


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
