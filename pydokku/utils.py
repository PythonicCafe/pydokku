import datetime
import re
import subprocess
from dataclasses import fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, List

REGEXP_DOKKU_HEADER = re.compile(r"^\s*=====> ", flags=re.MULTILINE)


def get_app_name(obj: Any) -> str | None:
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


def parse_timestamp(value: str | None) -> datetime.datetime | None:
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return datetime.datetime.fromtimestamp(int(value)).replace(tzinfo=get_system_tzinfo())


def parse_int(value: str | None) -> int | None:
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


def parse_bool(value: str | None) -> bool | None:
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


def parse_path(value: str | None) -> Path | None:
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


def parse_comma_separated_list(text: str | None) -> List[str]:
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


def parse_space_separated_list(text: str | None) -> List[str]:
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
    discards: List[str] | None = None,
    renames: dict[str, str] | None = None,
    parsers: dict[str, Callable[[str], Any]] | None = None,
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
                separator = line.find(":")
                key, value = line[:separator], line[separator + 1 :]
                if normalize_keys:
                    key = key.lower().replace(" ", "_")
                if renames is not None and key in renames:
                    key = renames[key]
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


def execute_command(command: list[str], stdin: str | None = None, check: bool = True) -> tuple[int, str, str]:
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
