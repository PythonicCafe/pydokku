from typing import Iterator, List, Type, TypeVar

from ..models import App, Command

T = TypeVar("T")


class DokkuPlugin:
    name: str = None
    object_class: Type[T] = None

    def __init__(self, dokku):
        self.dokku = dokku

    def _evaluate(
        self,
        operation: str,
        params: List[str] = None,
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

    def dump_all(self, apps: List[App], system: bool = True) -> List[dict]:
        """Dump all objects for this specific plugin

        The result must always be a list of dictionaries. Each dict must be enough to reconstruct an object for this
        class with `self.object_class(**dict)`.
        """
        raise NotImplementedError(f"Method `dump_all` not implemented for {self.__class__.__name__}")

    def create_object(self, obj: T, execute: bool = True) -> List[str] | List[Command]:
        """Create an object for this specific plugin or return list of commands to do it"""
        # XXX: this command MUST NOT run some commands and use the output of those commands to then execute new
        # commands. All actions executed by this method must rely solely on `obj` data provided so the actions can be
        # exported as commands correctly.
        # TODO: add option to not raise exception if object already exists
        raise NotImplementedError(f"Class {self.__class__.__name__} does not implement `create_object`")

    def create_objects(self, objs: List[T], execute: bool = True) -> Iterator[str] | Iterator[Command]:
        for obj in objs:
            yield from self.create_object(obj, execute=execute)

    # TODO: create CRUD methods:
    # TODO: create list_objects
    # TODO: create delete_object
