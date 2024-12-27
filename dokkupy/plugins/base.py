from typing import Type, TypeVar

T = TypeVar("T")


class DokkuPlugin:
    name: str = None
    object_class: Type[T] = None

    def __init__(self, dokku):
        self.dokku = dokku

    def _execute(self, command: str, params=None, stdin: str = None, check=True, sudo=False) -> str:
        cmd = ["dokku", f"{self.name}:{command}"]
        if params is not None:
            cmd.extend(params)
        return self.dokku._execute(cmd, stdin=stdin, check=check, sudo=sudo)

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
