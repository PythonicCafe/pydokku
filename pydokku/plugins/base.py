from typing import Iterator, List, Type, TypeVar

from ..models import App, Command
from ..utils import dataclass_field_set

T = TypeVar("T")


class DokkuPlugin:
    name: str = None
    object_classes: list[Type[T]] = []

    def __init__(self, dokku):
        self.dokku = dokku

    def _evaluate(
        self,
        operation: str,
        params: List[str] | None = None,
        stdin: str = None,
        check: bool = True,
        sudo: bool = False,
        execute: bool = True,
        full_return: bool = False,
    ) -> str | Command | tuple[int, str, str]:
        cmd = Command(
            command=["dokku", f"{self.name}:{operation}"] + (params if params is not None else []),
            stdin=stdin,
            check=check,
            sudo=sudo,
        )
        if not execute:
            return cmd
        return_code, stdout, stderr = self._execute(cmd)
        return stdout if not full_return else (return_code, stdout, stderr)

    def _execute(self, command: Command) -> tuple[int, str, str]:
        return self.dokku._execute(command)

    def object_list(self, apps: List[App], system: bool = True) -> List[T]:
        """List all objects for this specific plugin"""
        raise NotImplementedError(f"Method `object_list` not implemented for {self.__class__.__name__}")

    def object_deserialize(self, obj: dict) -> T:
        obj_keys = set(obj.keys())
        for DataClass in self.object_classes:
            if obj_keys == dataclass_field_set(DataClass):
                return DataClass(**obj)
        raise ValueError(f"Cannot deserialize object in {self.name}: {repr(obj)}")

    def object_create(self, obj: T, skip_system: bool = False, execute: bool = True) -> List[str] | List[Command]:
        """Create an object for this specific plugin or return list of commands to do it"""
        # XXX: this command MUST NOT run some commands and use the output of those commands to then execute new
        # commands. All actions executed by this method must rely solely on `obj` data provided so the actions can be
        # exported as commands correctly.
        raise NotImplementedError(f"Class {self.__class__.__name__} does not implement `object_create`")

    def object_create_many(
        self, objs: List[T], execute: bool = True
    ) -> Iterator[str] | Iterator[Command]:
        # The difference between this and calling `self.object_create` for each object is that this one yields only one
        # global command, so it's faster.
        for index, obj in enumerate(objs):
            yield from self.object_create(obj=obj, skip_system=index > 0, execute=execute)

    # TODO: define an interface for `ensure_object` and implement it in current plugins and in CLI (add TODOs for
    # testing this new method in each plugin and a general test with clean + apply + export1 + ensure + export2 + clean
    # + assert)
    # TODO: should implement object_delete?
