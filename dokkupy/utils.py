import datetime
from functools import lru_cache


@lru_cache
def get_system_tzinfo():
    return datetime.datetime.now().astimezone().tzinfo


def parse_timestamp(value):
    return datetime.datetime.fromtimestamp(int(value)).replace(tzinfo=get_system_tzinfo())


def parse_bool(value):
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return {"true": True, "t": True, "false": False, "f": False}[value]
