import datetime
import re
import subprocess
from dataclasses import fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, List

REGEXP_ERROR_STR = re.compile(r"^\s*!\s+ (.*)$")
REGEXP_DOKKU_HEADER = re.compile(r"^\s*=====> ", flags=re.MULTILINE)


@lru_cache
def dataclass_field_set(DataClass):
    return set([field.name for field in fields(DataClass)])


def clean_stderr(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    result = REGEXP_ERROR_STR.findall(text)
    if not result:
        raise ValueError(f"Cannot parse stderr message: {repr(value)}")
    return result[0]


@lru_cache
def get_system_tzinfo():
    return datetime.datetime.now().astimezone().tzinfo


def parse_timestamp(value):
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return datetime.datetime.fromtimestamp(int(value)).replace(tzinfo=get_system_tzinfo())


def parse_int(value):
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return int(value)


def parse_bool(value):
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return {"true": True, "t": True, "false": False, "f": False}[value]


def parse_path(value: str | None) -> Path | None:
    value = str(value or "").strip() if value else None
    if not value:
        return None
    return Path(value)


def parse_comma_separated_list(text):
    text = str(text or "").strip() if text else None
    if not text or text == "none":
        return []
    return text.split(",")


def parse_space_separated_list(text):
    text = str(text or "").strip() if text else None
    if not text:
        return []
    return text.split(" ")


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


def execute_command(command: list[str], stdin: str = None, check=True) -> tuple[int, str, str]:
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
