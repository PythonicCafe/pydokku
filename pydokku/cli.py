import argparse
import json
import os
import sys
from pathlib import Path
from textwrap import indent

from . import __version__
from .plugins.base import PluginScheduler


def create_dokku_instance(ssh_config: dict = None):
    from .dokku_cli import Dokku  # noqa

    ssh_config = ssh_config or {}
    return Dokku(
        ssh_host=ssh_config.get("host"),
        ssh_user=ssh_config.get("user"),
        ssh_port=ssh_config.get("port"),
        ssh_private_key=ssh_config.get("private_key"),
        ssh_key_password=ssh_config.get("key_password"),
        ssh_mux=ssh_config.get("mux"),
    )


def no_log(*args, **kwargs):
    return


def error_log(*args, **kwargs):
    if "file" not in kwargs:
        kwargs["file"] = sys.stderr
    if "flush" not in kwargs:
        kwargs["flush"] = True
    print(*args, **kwargs)


def dokku_export(json_filename: Path, ssh_config: dict, quiet: bool = False, indent: int = 2):
    errlog = no_log if quiet else error_log
    dokku = create_dokku_instance(ssh_config=ssh_config)
    data = {
        "pydokku": {"version": __version__},
        "dokku": {"version": dokku.version()},
    }
    # TODO: add a progress bar?
    errlog("Finding plugins...", end="")
    system_plugins = {plugin.name: plugin for plugin in dokku.plugin.list()}
    errlog(f" {len(system_plugins)} found.")
    errlog("Finding apps...", end="")
    apps = dokku.apps.list()
    errlog(f" {len(apps)} found.")
    exported_plugins = set()
    scheduler = PluginScheduler(plugins=dokku.plugins.values())
    plugin_batches = list(scheduler)
    required_cmd_warnings = []
    for plugin_batch in plugin_batches:
        # TODO: make the batch parallel?
        for name in plugin_batch:
            plugin = dokku.plugins[name]
            errlog(f"Listing and serializing objects for plugin {name}...", end="")
            plugin_name = plugin.plugin_name
            if plugin_name not in system_plugins:
                errlog(" not installed, skipping.")
                continue
            elif not system_plugins[plugin_name].enabled:
                errlog(" not enabled, skipping.")
                continue
            try:
                data[name] = [obj.serialize() for obj in plugin.object_list(apps, system=True)]
            except NotImplementedError:
                errlog(f"WARNING: cannot export data for plugin {repr(name)} (`object_list` method not implemened)")
            else:
                exported_plugins.add(plugin_name)
                errlog(f" {len(data[name])} exported.")
                if not dokku.can_execute_regular_commands and len(data[name]) > 0 and plugin.requires_extra_commands:
                    required_cmd_warnings.append(name)
    not_exported = set(system_plugins.keys()) - exported_plugins
    if not_exported:
        plural = "s" if len(system_plugins) != 1 else ""
        names = ", ".join(sorted(not_exported))
        errlog(f"WARNING: {len(not_exported)} plugin{plural} were not exported (not implemented): {names}")
    if required_cmd_warnings:
        plural = "s" if len(required_cmd_warnings) != 1 else ""
        names = ", ".join(sorted(required_cmd_warnings))
        errlog(
            f"WARNING: {len(required_cmd_warnings)} plugin{plural} were not completely exported because this user don't have enough access: {names}"
        )
    json_data = json.dumps(data, indent=indent, default=str)
    if json_filename.name == "-":
        print(json_data)
    else:
        json_filename.parent.mkdir(parents=True, exist_ok=True)
        json_filename.write_text(json_data)


def dokku_apply(json_filename: Path, ssh_config: dict, force: bool = False, quiet: bool = False, execute: bool = True):
    errlog = no_log if quiet else error_log
    input_file = json_filename if json_filename.name != "-" else sys.stdin
    with input_file.open() as fobj:
        data = json.load(fobj)
    data.pop("pydokku")
    dokku_metadata = data.pop("dokku")
    dokku = create_dokku_instance(ssh_config=ssh_config)
    expected_version = dokku_metadata["version"]
    current_version = dokku.version()
    if current_version != expected_version:
        if not force:
            print(
                f"ERROR: version mismatch (current: {current_version}, expected: {expected_version}). Use `--force` if you want to continue",
                file=sys.stderr,
            )
            exit(1)
        errlog(f"WARNING: version mismatch (current: {current_version}, expected: {expected_version}).")

    system_plugins = {plugin.name: plugin for plugin in dokku.plugin.list()}

    def process_plugin(name: str):
        plugin = dokku.plugins[name]
        plugin_name = plugin.plugin_name
        prefix = ("# " if not execute else "") + f"[{name}] "
        values = data.pop(name, None)
        if values is None:
            errlog(f"{prefix}No data found, skipping.")
            return
        elif plugin_name not in system_plugins:
            errlog(f"{prefix}Not found, skipping.")
            return
        elif not system_plugins[plugin_name].enabled:
            errlog(f"{prefix}Disabled, skipping.")
            return
        errlog(f"{prefix}Reading objects...", end="")
        objects = [plugin.object_deserialize(row) for row in values]
        errlog(f" {len(objects)} loaded.")
        errlog(f"{prefix}Creating objects")
        for result in plugin.object_create_many(objects, execute=execute):
            # `result` will be command's stdout (if execute) or Command object (if not execute)
            output = str(result).strip()
            if execute:
                output = indent(output, "    ")
            print(output)
            # TODO: add option to return output instead of printing

    scheduler = PluginScheduler(plugins=dokku.plugins.values())
    # Consume the entire scheduler so if there are any loops in the plugin dependency graph the exception will be
    # raised before doing anything.
    plugin_batches = list(scheduler)
    process_plugin("plugin")  # Must install all plugins before anything
    system_plugins = {plugin.name: plugin for plugin in dokku.plugin.list()}  # Update after installing new ones
    for plugin_batch in plugin_batches:
        # TODO: make the batch parallel?
        for name in plugin_batch:
            if name == "plugin":
                continue  # Done already
            process_plugin(name)
    if data:
        not_executed = list(data.keys())
        errlog(f"WARNING: remaining plugins not executed: {', '.join(not_executed)}")


def dependency_graph(output_filename: Path, ssh_config: dict, indent: int = 2):
    dokku = create_dokku_instance(ssh_config=ssh_config)
    scheduler = PluginScheduler(plugins=dokku.plugins.values())
    data = scheduler.graph()
    if output_filename.name == "-":
        print(data)
    else:
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        output_filename.write_text(data)


def main():
    # TODO: deal with `DOKKU_HOST` and git remotes on the current working directory, as Dokku does
    # <https://dokku.com/docs/deployment/remote-commands/>
    parser = argparse.ArgumentParser()

    parser.add_argument("--ssh-host", "-H", type=str)
    parser.add_argument("--ssh-user", "-u", type=str, default="dokku")
    parser.add_argument("--ssh-port", "-p", type=int, default=22)
    parser.add_argument("--ssh-private-key", "-k", type=Path)
    parser.add_argument("--ssh-key-password", "-P", type=str, help="Prefer to use SSH_KEY_PASSWORD env var")
    parser.add_argument("--no-ssh-mux", "-N", action="store_true", help="Disable SSH multiplexing")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Show current version of pydokku")

    export_parser = subparsers.add_parser("export", help="Export all metadata collected by plugins to JSON")
    export_parser.add_argument("--indent", "-i", type=int, default=2, help="Indentation level (in spaces)")
    export_parser.add_argument("--quiet", "-q", action="store_true", help="Do not show warnings on stderr")
    export_parser.add_argument("json_filename", type=Path, help="JSON filename to save data")
    # TODO: add options for filters (by app or plugin name)

    graph_parser = subparsers.add_parser("dependency-graph", help="Export a plugin dependency graph in graphviz (DOT) format")
    graph_parser.add_argument("--indent", "-i", type=int, default=2, help="Indentation level (in spaces)")
    graph_parser.add_argument("output_filename", type=Path, help="Filename to save the graph representation")

    apply_parser = subparsers.add_parser(
        "apply", help="Load a JSON specification and execute all needed operations in a Dokku installation"
    )
    apply_parser.add_argument("--force", "-f", action="store_true", help="Force execution even if version mismatches")
    apply_parser.add_argument("--quiet", "-q", action="store_true", help="Do not show warnings on stderr")
    apply_parser.add_argument(
        "--print-only",
        "-p",
        action="store_true",
        help="Print the commands to be executed instead of actually executing them",
    )
    apply_parser.add_argument("json_filename", type=Path, help="Filename created by `pydokku export` command")

    args = parser.parse_args()
    ssh_config = {
        "host": args.ssh_host,
        "user": args.ssh_user,
        "port": args.ssh_port,
        "private_key": args.ssh_private_key,
        "key_password": args.ssh_key_password or os.environ.get("SSH_KEY_PASSWORD"),
        "mux": not args.no_ssh_mux,
    }

    if args.command == "version":
        print(f"pydokku {__version__}")
    elif args.command == "export":
        dokku_export(
            json_filename=args.json_filename,
            ssh_config=ssh_config,
            quiet=args.quiet,
            indent=args.indent,
        )
    elif args.command == "apply":
        dokku_apply(
            json_filename=args.json_filename,
            force=args.force,
            quiet=args.quiet,
            execute=not args.print_only,
            ssh_config=ssh_config,
        )
    elif args.command == "dependency-graph":
        dependency_graph(
            output_filename=args.output_filename,
            ssh_config=ssh_config,
            indent=args.indent,
        )


if __name__ == "__main__":
    main()
