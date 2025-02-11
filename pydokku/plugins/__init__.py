from .apps import AppsPlugin  # noqa
from .checks import ChecksPlugin  # noqa
from .config import ConfigPlugin  # noqa
from .domains import DomainsPlugin  # noqa
from .git import GitPlugin  # noqa
from .letsencrypt import LetsEncryptPlugin  # noqa
from .maintenance import MaintenancePlugin  # noqa
from .network import NetworkPlugin  # noqa
from .nginx import NginxPlugin  # noqa
from .plugin import PluginPlugin  # noqa
from .ports import PortsPlugin  # noqa
from .proxy import ProxyPlugin  # noqa
from .ps import PsPlugin  # noqa
from .redirect import RedirectPlugin  # noqa
from .ssh_keys import SSHKeysPlugin  # noqa
from .storage import StoragePlugin  # noqa


# Service plugins - maybe add service:links (service:info is per service and costly)

# TODO: implement postgres:create <service> [--create-flags...]                                   create a Postgres service
# TODO: implement postgres:destroy <service> [-f|--force]                                         delete the Postgres service/data/container if there are no links left
# TODO: implement postgres:expose <service> <ports...>                                            expose a Postgres service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement postgres:unexpose <service>                                                     unexpose a previously exposed Postgres service
# TODO: implement postgres:link <service> <app> [--link-flags...]                                 link the Postgres service to the app
# TODO: implement postgres:unlink <service> <app>                                                 unlink the Postgres service from the app
# TODO: implement postgres:info <service> [--single-info-flag]                                    print the service information
# TODO: implement postgres:logs <service> [-t|--tail] [<tail-num>]                                print the most recent log(s) for this service
# TODO: implement postgres:list                                                                   list all Postgres services
# TODO: implement postgres:pause <service>                                                        pause a running Postgres service
# TODO: implement postgres:restart <service>                                                      graceful shutdown and restart of the Postgres service container
# TODO: implement postgres:start <service>                                                        start a previously stopped Postgres service
# TODO: implement postgres:stop <service>                                                         stop a running Postgres service
# TODO: implement postgres:promote <service> <app>                                                promote service <service> as DATABASE_URL in <app>
# TODO: implement postgres:set <service> <key> <value>                                            set or clear a property for a service
# TODO: implement postgres:upgrade <service> [--upgrade-flags...]                                 upgrade service <service> to the specified versions

# TODO: implement mariadb:create <service> [--create-flags...]                                   create a MariaDB service
# TODO: implement mariadb:destroy <service> [-f|--force]                                         delete the MariaDB service/data/container if there are no links left
# TODO: implement mariadb:expose <service> <ports...>                                            expose a MariaDB service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement mariadb:unexpose <service>                                                     unexpose a previously exposed MariaDB service
# TODO: implement mariadb:link <service> <app> [--link-flags...]                                 link the MariaDB service to the app
# TODO: implement mariadb:unlink <service> <app>                                                 unlink the MariaDB service from the app
# TODO: implement mariadb:info <service> [--single-info-flag]                                    print the service information
# TODO: implement mariadb:logs <service> [-t|--tail] [<tail-num>]                                print the most recent log(s) for this service
# TODO: implement mariadb:list                                                                   list all MariaDB services
# TODO: implement mariadb:pause <service>                                                        pause a running MariaDB service
# TODO: implement mariadb:restart <service>                                                      graceful shutdown and restart of the MariaDB service container
# TODO: implement mariadb:start <service>                                                        start a previously stopped MariaDB service
# TODO: implement mariadb:stop <service>                                                         stop a running MariaDB service
# TODO: implement mariadb:promote <service> <app>                                                promote service <service> as DATABASE_URL in <app>
# TODO: implement mariadb:set <service> <key> <value>                                            set or clear a property for a service
# TODO: implement mariadb:upgrade <service> [--upgrade-flags...]                                 upgrade service <service> to the specified versions

# TODO: implement mysql:create <service> [--create-flags...]         # create a mysql service
# TODO: implement mysql:destroy <service> [-f|--force]               # delete the mysql service/data/container if there are no links left
# TODO: implement mysql:expose <service> <ports...>                  # expose a mysql service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement mysql:unexpose <service>                           # unexpose a previously exposed mysql service
# TODO: implement mysql:link <service> <app> [--link-flags...]       # link the mysql service to the app
# TODO: implement mysql:unlink <service> <app>                       # unlink the mysql service from the app
# TODO: implement mysql:info <service> [--single-info-flag]          # print the service information
# TODO: implement mysql:logs <service> [-t|--tail] <tail-num-optional> # print the most recent log(s) for this service
# TODO: implement mysql:list                                         # list all mysql services
# TODO: implement mysql:pause <service>                              # pause a running mysql service
# TODO: implement mysql:restart <service>                            # graceful shutdown and restart of the mysql service container
# TODO: implement mysql:start <service>                              # start a previously stopped mysql service
# TODO: implement mysql:stop <service>                               # stop a running mysql service
# TODO: implement mysql:promote <service> <app>                      # promote service <service> as DATABASE_URL in <app>
# TODO: implement mysql:set <service> <key> <value>                  # set or clear a property for a service
# TODO: implement mysql:upgrade <service> [--upgrade-flags...]       # upgrade service <service> to the specified versions

# TODO: implement redis:create <service> [--create-flags...]                                   create a Redis service
# TODO: implement redis:destroy <service> [-f|--force]                                         delete the Redis service/data/container if there are no links left
# TODO: implement redis:expose <service> <ports...>                                            expose a Redis service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement redis:unexpose <service>                                                     unexpose a previously exposed Redis service
# TODO: implement redis:link <service> <app> [--link-flags...]                                 link the Redis service to the app
# TODO: implement redis:unlink <service> <app>                                                 unlink the Redis service from the app
# TODO: implement redis:info <service> [--single-info-flag]                                    print the service information
# TODO: implement redis:logs <service> [-t|--tail] [<tail-num>]                                print the most recent log(s) for this service
# TODO: implement redis:list                                                                   list all Redis services
# TODO: implement redis:pause <service>                                                        pause a running Redis service
# TODO: implement redis:restart <service>                                                      graceful shutdown and restart of the Redis service container
# TODO: implement redis:start <service>                                                        start a previously stopped Redis service
# TODO: implement redis:stop <service>                                                         stop a running Redis service
# TODO: implement redis:promote <service> <app>                                                promote service <service> as REDIS_URL in <app>
# TODO: implement redis:set <service> <key> <value>                                            set or clear a property for a service
# TODO: implement redis:upgrade <service> [--upgrade-flags...]                                 upgrade service <service> to the specified versions

# TODO: implement elasticsearch:create <service> [--create-flags...]                         create a Elasticsearch service
# TODO: implement elasticsearch:destroy <service> [-f|--force]                               delete the Elasticsearch service/data/container if there are no links left
# TODO: implement elasticsearch:expose <service> <ports...>                                  expose a Elasticsearch service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement elasticsearch:unexpose <service>                                           unexpose a previously exposed Elasticsearch service
# TODO: implement elasticsearch:info <service> [--single-info-flag]                          print the service information
# TODO: implement elasticsearch:link <service> <app> [--link-flags...]                       link the Elasticsearch service to the app
# TODO: implement elasticsearch:list                                                         list all Elasticsearch services
# TODO: implement elasticsearch:logs <service> [-t|--tail] [<tail-num>]                      print the most recent log(s) for this service
# TODO: implement elasticsearch:pause <service>                                              pause a running Elasticsearch service
# TODO: implement elasticsearch:promote <service> <app>                                      promote service <service> as ELASTICSEARCH_URL in <app>
# TODO: implement elasticsearch:restart <service>                                            graceful shutdown and restart of the Elasticsearch service container
# TODO: implement elasticsearch:set <service> <key> <value>                                  set or clear a property for a service
# TODO: implement elasticsearch:start <service>                                              start a previously stopped Elasticsearch service
# TODO: implement elasticsearch:stop <service>                                               stop a running Elasticsearch service
# TODO: implement elasticsearch:unlink <service> <app>                                       unlink the Elasticsearch service from the app
# TODO: implement elasticsearch:upgrade <service> [--upgrade-flags...]                       upgrade service <service> to the specified versions

# TODO: implement rabbitmq:create <service> [--create-flags...]      # create a rabbitmq service
# TODO: implement rabbitmq:destroy <service> [-f|--force]            # delete the rabbitmq service/data/container if there are no links left
# TODO: implement rabbitmq:expose <service> <ports...>               # expose a rabbitmq service on custom host:port if provided (random port on the 0.0.0.0 interface if otherwise unspecified)
# TODO: implement rabbitmq:unexpose <service>                        # unexpose a previously exposed rabbitmq service
# TODO: implement rabbitmq:link <service> <app> [--link-flags...]    # link the rabbitmq service to the app
# TODO: implement rabbitmq:unlink <service> <app>                    # unlink the rabbitmq service from the app
# TODO: implement rabbitmq:info <service> [--single-info-flag]       # print the service information
# TODO: implement rabbitmq:logs <service> [-t|--tail] <tail-num-optional> # print the most recent log(s) for this service
# TODO: implement rabbitmq:list                                      # list all rabbitmq services
# TODO: implement rabbitmq:pause <service>                           # pause a running rabbitmq service
# TODO: implement rabbitmq:restart <service>                         # graceful shutdown and restart of the rabbitmq service container
# TODO: implement rabbitmq:start <service>                           # start a previously stopped rabbitmq service
# TODO: implement rabbitmq:stop <service>                            # stop a running rabbitmq service
# TODO: implement rabbitmq:promote <service> <app>                   # promote service <service> as RABBITMQ_URL in <app>
# TODO: implement rabbitmq:set <service> <key> <value>               # set or clear a property for a service
# TODO: implement rabbitmq:upgrade <service> [--upgrade-flags...]    # upgrade service <service> to the specified versions
