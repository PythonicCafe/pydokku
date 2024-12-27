import datetime
import subprocess
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


def execute_command(command: list[str], stdin: str = None, check=True) -> tuple[int, str, str]:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if stdin is not None:
        process.stdin.write(stdin)
        process.stdin.close()
    result = process.wait()
    if check:
        assert result == 0, (
            f"Command {command} exited with status {result} "
            f"(stdout: {repr(process.stdout.read())}, stderr: {repr(process.stderr.read())})"
        )
    return result, process.stdout.read(), process.stderr.read()
