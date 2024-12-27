from dataclasses import asdict, dataclass
from typing import List


@dataclass
class Command:
    command: List[str]
    stdin: str = None
    check: bool = True
    sudo: bool = False

    def serialize(self):
        return asdict(self)
