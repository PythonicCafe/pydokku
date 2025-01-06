import argparse
import os
from pathlib import Path
from textwrap import indent


def create_dokku_instance(args):
    from .dokku_cli import Dokku  # noqa

    return Dokku(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_private_key=args.ssh_private_key,
        ssh_key_password=args.ssh_key_password or os.environ.get("SSH_KEY_PASSWORD"),
        ssh_mux=not args.no_ssh_mux,
    )


def dokku_dump(args):
    import json
    import sys

    dokku = create_dokku_instance(args)
    data = {
        "dokku": {"version": dokku.version()},
    }
    # TODO: if for some reason a plugin cannot export the data completely (eg: storage running via SSH as dokku user,
    # or ssh-keys running via SSH as dokku user), then print a warning on stderr.
    # TODO: add debugging log for each found plugin etc.?
    # TODO: add a progress bar?
    print("Finding apps...", file=sys.stderr, end="", flush=True)
    apps = dokku.apps.list()
    print(f" {len(apps)} found.", file=sys.stderr, flush=True)
    # TODO: add option to filter by app name and/or global
    for name, plugin in dokku.plugins.items():
        print(f"Dumping {name}...", file=sys.stderr, end="", flush=True)
        try:
            data[name] = plugin.dump_all(apps, system=True)
        except NotImplementedError:
            if not args.quiet:
                print(
                    f"WARNING: cannot export data for plugin {repr(name)} (`dump` method not implemened)",
                    file=sys.stderr,
                )
        else:
            print(f" {len(data[name])} exported.", file=sys.stderr, flush=True)

    if args.json_filename.name != "-":
        args.json_filename.parent.mkdir(parents=True, exist_ok=True)
        with args.json_filename.open(mode="w") as fobj:
            json.dump(data, fobj, indent=args.indent, default=str)
    else:
        print(json.dumps(data, indent=args.indent, default=str))


def dokku_load(args):
    import json
    import sys

    input_file = args.json_filename if args.json_filename.name != "-" else sys.stdin
    with input_file.open() as fobj:
        data = json.load(fobj)
    metadata = data.pop("dokku")
    dokku = create_dokku_instance(args)
    expected_version = metadata["version"]
    current_version = dokku.version()
    if current_version != expected_version:
        if not args.force:
            print(
                f"ERROR: version mismatch (current: {current_version}, expected: {expected_version}). Use `--force` if you want to continue"
            )
            exit(1)
        elif not args.quiet:
            print(
                f"WARNING: version mismatch (current: {current_version}, expected: {expected_version}).",
                file=sys.stderr,
            )
    execute = not args.print_only
    # TODO: ordering is important! may first get apps and then pass the list of apps to each plugin
    for key, values in sorted(data.items()):
        prefix = ("# " if not execute else "") + f"[{key}] "
        if not hasattr(dokku, key):
            print(f"WARNING: skipping unknown plugin {repr(key)}", file=sys.stderr)
            continue
        print(f"{prefix}Reading objects...", flush=True, end="")
        plugin = getattr(dokku, key)
        objects = [plugin.object_class(**row) for row in values]
        print(f" {len(objects)} loaded.")
        print(f"{prefix}Creating objects")
        for result in plugin.create_objects(objects, execute=execute):
            # `result` will be command's stdout (if execute) or Command object (if not execute)
            output = str(result).strip()
            if execute:
                output = indent(output, "    ")
            print(output)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--ssh-host", "-H", type=str)
    parser.add_argument("--ssh-user", "-u", type=str, default="dokku")
    parser.add_argument("--ssh-port", "-p", type=int, default=22)
    parser.add_argument("--ssh-private-key", "-k", type=Path)
    parser.add_argument("--ssh-key-password", "-P", type=str, help="Prefer to use SSH_KEY_PASSWORD env var")
    parser.add_argument("--no-ssh-mux", "-N", action="store_true", help="Disable SSH multiplexing")

    subparsers = parser.add_subparsers(dest="command", required=True)

    dump_parser = subparsers.add_parser("dump", help="")
    dump_parser.add_argument("--indent", "-i", type=int, default=2, help="Indentation level (in spaces)")
    dump_parser.add_argument("--quiet", "-q", action="store_true", help="Do not show warnings on stderr")
    dump_parser.add_argument("json_filename", type=Path, help="JSON filename to save data")
    # TODO: add options for filters

    load_parser = subparsers.add_parser(
        "load", help="Load a JSON specification and execute all needed operations in a Dokku installation"
    )
    load_parser.add_argument("--force", "-f", action="store_true", help="Force execution even if version mismatches")
    load_parser.add_argument("--quiet", "-q", action="store_true", help="Do not show warnings on stderr")
    load_parser.add_argument(
        "--print-only",
        "-p",
        action="store_true",
        help="Print the commands to be executed instead of actually executing them",
    )
    load_parser.add_argument("json_filename", type=Path, help="Filename created by `dokkupy dump` command")

    args = parser.parse_args()

    if args.command == "dump":
        dokku_dump(args)
    elif args.command == "load":
        dokku_load(args)


if __name__ == "__main__":
    main()
