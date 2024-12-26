# `apt install python3-dotenv` OR `pip install python3-dotenv`
import datetime
import json
import os
from pathlib import Path

from dotenv import dotenv_values  # TODO: remove this dependency?

# Env vars as in `/usr/bin/dokku`
DOKKU_LIB_ROOT = Path(os.environ.get("DOKKU_LIB_ROOT", "/var/lib/dokku/"))
DOKKU_ROOT = Path(os.environ.get("DOKKU_ROOT", "~dokku")).expanduser()
# export PLUGIN_PATH=${PLUGIN_PATH:="$DOKKU_LIB_ROOT/plugins"}
# export PLUGIN_AVAILABLE_PATH=${PLUGIN_AVAILABLE_PATH:="$PLUGIN_PATH/available"}
# export PLUGIN_ENABLED_PATH=${PLUGIN_ENABLED_PATH:="$PLUGIN_PATH/enabled"}
# export PLUGIN_CORE_PATH=${PLUGIN_CORE_PATH:="$DOKKU_LIB_ROOT/core-plugins"}
# export PLUGIN_CORE_AVAILABLE_PATH=${PLUGIN_CORE_AVAILABLE_PATH:="$PLUGIN_CORE_PATH/available"}
# export PLUGIN_CORE_ENABLED_PATH=${PLUGIN_CORE_ENABLED_PATH:="$PLUGIN_CORE_PATH/enabled"}


def directory_size(path: Path):
    """Return directory (with all its contents, recursively) size in bytes"""
    return sum(child.stat().st_size for child in path.glob("**/*"))


def read_env_file(filename: Path | str) -> dict:
    """Return env files as in `https://github.com/dokku/dokku/blob/master/plugins/config/environment.go`"""
    return dotenv_values(filename)


def read_vhost_file(filename: Path | str) -> list[str]:
    """Return virtual hosts from VHOST file"""
    # TODO: mention the source dokku code that generates this file
    with Path(filename).open() as fobj:
        return [item.strip() for item in fobj.readlines()]


def read_redirects_file(filename: Path | str) -> list[dict]:
    """Return redirects from REDIRECTS file"""
    # TODO: mention the source dokku code that generates this file
    result = []
    with Path(filename).open() as fobj:
        for line in fobj.readlines():
            line = line.strip()
            source, destination, status_code = line.split(":")
            result.append({"source": source, "destination": destination, "status_code": status_code})
    return result


def parse_docker_options(filename: Path):
    data = {"links": [], "storage": []}
    with filename.open() as fobj:
        for line in fobj:
            option, parameters = line.strip().split(maxsplit=1)
            if option == "--link":
                service_detail, hostname = parameters.split(":", maxsplit=1)
                _, service, name = service_detail.split(".", maxsplit=3)
                data["links"].append({"service": service, "name": name, "hostname": hostname})
            elif option == "-v":
                host_path, container_path = parameters.split(":", maxsplit=1)
                data["storage"].append({"host_path": host_path, "container_path": container_path})
            else:
                print(f"WARNING: line not processed {repr(line)}")
    return data


class Dokku:
    """Interfaces with Dokku reading the files it creates"""

    def __init__(self, lib_path: Path | str = DOKKU_LIB_ROOT, root_path: str | Path = DOKKU_ROOT):
        self.lib_path = Path(lib_path)
        self.root_path = Path(root_path)

    def version(self) -> str:
        """Return version as in `/var/lib/dokku/core-plugins/enabled/common/functions`"""
        for filename in (self.lib_path / "STABLE_VERSION", self.lib_path / "VERSION"):
            if filename.exists():
                with filename.open() as fobj:
                    return fobj.read().strip()

    def apps(self) -> list[str]:
        apps_paths = self.lib_path / "config" / "apps"
        return [app_path.name for app_path in apps_paths.glob("*")]

    def app_info(self, app_name: str):
        app_path = self.lib_path / "config" / "apps" / app_name
        app = {"name": app_name}
        for filename in app_path.glob("*"):
            with filename.open(mode="r") as fobj:
                app[filename.name.replace("-", "_")] = fobj.read()
        if app.get("created_at"):
            app["created_at"] = datetime.datetime.fromtimestamp(int(app["created_at"]))

        app_home = self.root_path / app_name
        app.update(
            {
                "domains": [],
                "env": {},
                "links": [],
                "redirects": [],
                "storage": [],
            }
        )
        docker_run_options_filename = app_home / "DOCKER_OPTIONS_RUN"
        if docker_run_options_filename.exists():
            docker_run_options = parse_docker_options(docker_run_options_filename)
            for key, values in docker_run_options.items():
                for value in values:
                    app[key].append(value)
        env_filename = app_home / "ENV"
        if env_filename.exists():
            app["env"].update(read_env_file(env_filename))
        vhost_filename = app_home / "VHOST"
        if vhost_filename.exists():
            app["domains"].extend(read_vhost_file(vhost_filename))
        redirects_filename = app_home / "REDIRECTS"
        if redirects_filename.exists():
            app["redirects"].extend(read_redirects_file(redirects_filename))
        # TODO: read other home files
        # CONTAINER.web.1
        # CONTAINER.worker.1
        # IP.web.1
        # IP.worker.1
        # PORT.web.1
        # DOCKER_OPTIONS_BUILD
        # DOCKER_OPTIONS_DEPLOY
        # TODO: read dokku code to check other files
        return app

    def plugins(self) -> list[str]:
        plugins_path = self.lib_path / "plugins" / "enabled"
        return [plugin.name for plugin in plugins_path.glob("*")]

    def services(self) -> list[str]:
        services_path = self.lib_path / "services"
        return [service.name for service in services_path.glob("*")]

    def service_list(self, service_type: str) -> list[str]:
        service_path = self.lib_path / "services" / service_type
        return [service.name for service in service_path.glob("*")]

    def service_info(self, service_type: str, service_name: str) -> dict:
        """Retrieve information for a generic service, such as `dokku <service>:info <name>`"""
        service_path = self.lib_path / "services" / service_type / service_name
        result = {
            "name": service_name,
            "type": service_type,
            "size": directory_size(service_path),
        }
        for filename in service_path.glob("*"):
            if not filename.is_file():
                continue
            config_name = filename.name.lower()
            with filename.open() as fobj:
                value = fobj.read().strip()
                if config_name == "links":
                    value = value.splitlines()
                result[config_name] = value
        return result


if __name__ == "__main__":
    dokku = Dokku()
    result = {
        "dokku": {"version": dokku.version()},
        "plugins": dokku.plugins(),  # TODO: add plugin info?
        "apps": [dokku.app_info(app_name) for app_name in sorted(dokku.apps())],
        "services": [
            dokku.service_info(service_type, service_name)
            for service_type in sorted(dokku.services())
            for service_name in sorted(dokku.service_list(service_type))
        ],
    }
    # TODO: read other plugin's code to check most used files
    print(json.dumps(result, indent=2, default=str))
