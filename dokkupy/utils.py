import datetime
import re
import subprocess
from functools import lru_cache

REGEXP_ERROR_STR = re.compile(r"^\s*!\s+ (.*)$")


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
    return datetime.datetime.fromtimestamp(int(value)).replace(tzinfo=get_system_tzinfo())


def parse_bool(value):
    value = str(value if value is not None else "").lower()
    if not value:
        return None
    return {"true": True, "t": True, "false": False, "f": False}[value]


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
