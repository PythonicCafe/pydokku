from typing import List, Type, TypeVar

from ..models import Command

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

    def dump(self):
        if hasattr(self, "list"):
            return [obj.serialize() for obj in self.list()]
        raise NotImplementedError(f"Method `dump` not implemented for {self.__class__.__name__}")

    def ensure_object(self, obj: T):
        raise NotImplementedError(f"Class {self.__class__.__name__} does not implement `ensure_object`")

    def load(self, data: T | dict, execute: bool = True):
        if isinstance(data, self.object_class):
            obj = data
        elif isinstance(data, dict):
            obj = self.object_class(**data)
        else:
            raise ValueError(
                f"`data` must be either `{self.object_class}` or its serialized version as a `dict` (got: {type(data)})"
            )
        self.ensure_object(obj, execute=execute)
