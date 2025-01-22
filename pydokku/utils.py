import datetime
import re
import subprocess
from dataclasses import fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union

REGEXP_DOKKU_HEADER = re.compile(r"^\s*=====> ", flags=re.MULTILINE)
REGEXP_ISO_FORMAT = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[ T]([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?(.*)?")


def get_app_name(obj: Any) -> Union[str, None]:
    return obj.app_name


@lru_cache
def dataclass_field_set(DataClass) -> List[str]:
    return set([field.name for field in fields(DataClass)])


def clean_stderr(value: str) -> str:
    """
    >>> clean_stderr('')
    ''
    >>> clean_stderr('Some text')
    'Some text'
    >>> clean_stderr('!     Key specified in is not a valid ssh public key')
    'Key specified in is not a valid ssh public key'
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if text[0] == "!":
        text = text[1:].strip()
    return text


@lru_cache
def get_system_tzinfo() -> datetime.timezone:
    return datetime.datetime.now().astimezone().tzinfo


def parse_timestamp(value: Union[str, None]) -> Union[datetime.datetime, None]:
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return datetime.datetime.fromtimestamp(int(value)).replace(tzinfo=get_system_tzinfo())


def parse_iso_format(value: Union[str, None]) -> Union[datetime.datetime, None]:
    """
    >>> parse_iso_format('2024-02-25T01:55:24.275184461Z')
    datetime.datetime(2024, 2, 25, 1, 55, 24, 275184, tzinfo=datetime.timezone.utc)
    >>> parse_iso_format('2024-02-25T01:55:24Z')
    datetime.datetime(2024, 2, 25, 1, 55, 24, tzinfo=datetime.timezone.utc)
    >>> parse_iso_format('2024-02-25T01:55:24')
    datetime.datetime(2024, 2, 25, 1, 55, 24)
    """
    original_value = value
    value = str(value if value is not None else "")
    if not value:
        return None
    # Custom parse_iso_format to work on Python 3.10 and below
    result = REGEXP_ISO_FORMAT.findall(value)
    if not result:
        raise ValueError(f"Value {repr(original_value)} is not in ISO datetime format")
    date, time, microseconds, timezone = result[0]
    timezone = "+00:00" if timezone.lower() == "z" else timezone
    dt = datetime.datetime.fromisoformat(f"{date}T{time}{timezone}")
    if microseconds:
        dt = dt.replace(microsecond=int(microseconds[1:7]))
    return dt


def parse_timedelta_seconds(value: Union[str, None]) -> Union[datetime.timedelta, None]:
    """
    Parse a seconds value
    >>> import datetime
    >>> print(parse_timedelta_seconds(""))
    None
    >>> print(parse_timedelta_seconds(None))
    None
    >>> parse_timedelta_seconds("15724800")
    datetime.timedelta(days=182)
    >>> parse_timedelta_seconds(15724800)
    datetime.timedelta(days=182)
    """
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return datetime.timedelta(seconds=int(value))


def parse_int(value: Union[str, None]) -> Union[int, None]:
    """
    >>> print(parse_int(""))
    None
    >>> parse_int("123")
    123
    >>> type(parse_int("123"))
    <class 'int'>
    """
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return int(value)


def parse_bool(value: Union[str, None]) -> Union[bool, None]:
    """
    >>> print(parse_bool(""))
    None
    >>> parse_bool("true")
    True
    >>> parse_bool("false")
    False
    >>> type(parse_bool("true"))
    <class 'bool'>
    >>> parse_bool("true") == parse_bool("t") == parse_bool("True") == parse_bool("T")
    True
    >>> parse_bool("false") == parse_bool("f") == parse_bool("False") == parse_bool("F")
    True
    """
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return {"true": True, "t": True, "false": False, "f": False}[value]


def parse_path(value: Union[str, None]) -> Union[Path, None]:
    """
    >>> from pathlib import Path
    >>> print(parse_path(""))
    None
    >>> isinstance(parse_path("file.ext"), Path)
    True
    """
    value = str(value or "").strip() if value else None
    if not value:
        return None
    return Path(value)


def parse_comma_separated_list(text: Union[str, None]) -> List[str]:
    """
    >>> parse_comma_separated_list("")
    []
    >>> parse_comma_separated_list('abc,123",456')
    ['abc', '123"', '456']
    """
    text = str(text or "").strip() if text else None
    if not text or text == "none":
        return []
    return text.split(",")


def parse_space_separated_list(text: Union[str, None]) -> List[str]:
    """
    >>> parse_space_separated_list("")
    []
    >>> parse_space_separated_list('   abc 123"    456')
    ['abc', '123"', '456']
    """
    text = str(text or "").strip() if text else None
    if not text:
        return []
    return [item for item in text.strip().split(" ") if item]


def get_stdout_rows_parser(
    normalize_keys: bool = False,
    discards: Union[List[str], None] = None,
    renames: Union[Dict[str, str], None] = None,
    parsers: Union[Dict[str, Callable[[str], Any]], None] = None,
    separator: str = "_",
    remove_prefix=None,
) -> Callable:
    """Returns a function that parses stdout and returns a list of rows, already converted/parsed based on configs"""

    known_output_fields = []
    if renames is not None:
        for field_name in renames.values():
            if field_name not in known_output_fields:
                known_output_fields.append(field_name)
    if parsers is not None:
        for field_name in parsers.keys():
            if field_name not in known_output_fields:
                known_output_fields.append(field_name)
    base_row = {key: None for key in known_output_fields}

    def func(stdout: str) -> List[dict]:
        result = []
        for row_text in REGEXP_DOKKU_HEADER.split(stdout.strip())[1:]:
            lines = row_text.strip().splitlines()
            row_app_name, _ = lines[0].split(maxsplit=1)
            app_name_key = "app_name" if renames is None else renames.get("app_name", "app_name")
            row = base_row.copy()
            row[app_name_key] = row_app_name
            for line in lines[1:]:
                line = line.strip()
                stop = line.find(":")
                key, value = line[:stop], line[stop + 1 :]
                if normalize_keys:
                    key = key.lower().replace(" ", separator)
                if renames is not None and key in renames:
                    key = renames[key]
                if remove_prefix is not None and key.startswith(remove_prefix):
                    key = key[len(remove_prefix) :]
                if discards is not None and key in discards:
                    continue
                value = value.strip()
                if parsers is not None and key in parsers:
                    value = parsers[key](value)
                elif not value:
                    value = None
                row[key] = value
            result.append(row)
        return result

    return func


def execute_command(command: List[str], stdin: Union[str, None] = None, check: bool = True) -> Tuple[int, str, str]:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    stdout, stderr = process.communicate(input=stdin)
    result = process.returncode
    if check and result != 0:
        raise RuntimeError(
            f"Command {command} exited with status {result} (stdout: {repr(stdout)}, stderr: {repr(stderr)})"
        )
    return result, stdout, stderr
