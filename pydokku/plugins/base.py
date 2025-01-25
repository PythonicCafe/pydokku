from collections import defaultdict
from itertools import groupby
from typing import Any, Iterator, List, Tuple, Type, TypeVar, Union

from ..models import App, Command
from ..utils import dataclass_field_set

T = TypeVar("T")


class DokkuPlugin:
    name: str = None  # This is pydokku internal name for the plugin. Use `_` instead of `-`
    subcommand: str = None  # Dokku subcommand related to this plugin. Usually equals to name.replace("_", "-")
    plugin_name: str = (
        None  # Name Dokku shows in `plugin:list` - could be different from plugin_name (like with a "-vhosts" suffix)
    )
    object_classes: List[Type[T]] = []
    requires: Tuple[str] = None  # Name of the plugins required by this one (property `name` of the dependencies)
    requires_extra_commands: bool = (
        None  # Requires extra commands to be executed to export all data required to recreate the same environment
    )

    def __init__(self, dokku):
        self.dokku = dokku

    def _evaluate(
        self,
        operation: Union[str, None],
        params: Union[List[str], None] = None,
        stdin: str = None,
        check: bool = True,
        sudo: bool = False,
        execute: bool = True,
        full_return: bool = False,
    ) -> Union[str, Command, Tuple[int, str, str]]:
        subcommand = f"{self.subcommand}:{operation}" if operation is not None else self.subcommand
        cmd = Command(
            command=["dokku", subcommand] + (params if params is not None else []),
            stdin=stdin,
            check=check,
            sudo=sudo,
        )
        if not execute:
            return cmd
        return_code, stdout, stderr = self._execute(cmd)
        return stdout if not full_return else (return_code, stdout, stderr)

    def _execute(self, command: Command) -> Tuple[int, str, str]:
        return self.dokku._execute(command)

    def object_list(self, apps: List[App], system: bool = True) -> List[T]:
        """List all objects for this specific plugin"""
        # TODO: should always sort (as network objects are sort in `test_export_apply`?)
        raise NotImplementedError(f"Method `object_list` not implemented for {self.__class__.__name__}")

    def object_deserialize(self, obj: dict) -> T:
        obj_keys = set(obj.keys())
        for DataClass in self.object_classes:
            if obj_keys == dataclass_field_set(DataClass):
                return DataClass(**obj)
        raise ValueError(f"Cannot deserialize object in {self.name}: {repr(obj)}")

    def object_create(self, obj: T, skip_system: bool = False, execute: bool = True) -> Union[List[str], List[Command]]:
        """Create an object for this specific plugin or return list of commands to do it"""
        # XXX: this command MUST NOT run some commands and use the output of those commands to then execute new
        # commands. All actions executed by this method must rely solely on `obj` data provided so the actions can be
        # exported as commands correctly.
        raise NotImplementedError(f"Class {self.__class__.__name__} does not implement `object_create`")

    def object_create_many(self, objs: List[T], execute: bool = True) -> Union[Iterator[str], Iterator[Command]]:
        # The difference between this and calling `self.object_create` for each object is that this one yields only one
        # global command, so it's faster.
        # Since a plugin can have many object types, we batch the execution for each type, this way each of them can
        # properly receive the `skip_system` parameter. The order of `object_classes` parameter is respected.
        type_order = {type_: index for index, type_ in enumerate(self.object_classes)}
        objs.sort(key=lambda obj: type_order[type(obj)])
        for _, group_objs in groupby(objs, key=type):
            for index, obj in enumerate(group_objs):
                yield from self.object_create(obj=obj, skip_system=index > 0, execute=execute)

    # TODO: define an interface for `ensure_object` and implement it in current plugins and in CLI (add TODOs for
    # testing this new method in each plugin and a general test with clean + apply + export1 + ensure + export2 + clean
    # + assert)
    # TODO: should implement object_delete?


class PluginScheduler:
    """Resolve dependencies between a list of plugins to ensure the correct order of execution"""

    def __init__(self, plugins: List[Any]):
        self.plugins = {plugin.name: plugin for plugin in plugins}
        self.remaining = list(self.plugins.keys())
        self.completed = set()
        self.dependency_count = {name: len(plugin.requires) for name, plugin in self.plugins.items()}
        self.dependents = defaultdict(list)
        for plugin in plugins:
            for dep in plugin.requires:
                self.dependents[dep].append(plugin.name)

    def __iter__(self):
        return self

    def __next__(self):
        ready = [plugin_name for plugin_name in self.remaining if self.dependency_count[plugin_name] == 0]
        if not ready:
            if self.remaining:
                raise RuntimeError(f"Detected inconsistency in plugin requirements - remaining: {self.remaining}")
            raise StopIteration
        for plugin_name in ready:
            self.remaining.remove(plugin_name)
            self.completed.add(plugin_name)
            for dependent in self.dependents[plugin_name]:
                self.dependency_count[dependent] -= 1
        return ready
