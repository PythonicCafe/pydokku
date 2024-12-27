class DokkuPlugin:
    name = None

    def __init__(self, dokku):
        self.dokku = dokku

    def _execute(self, command: str, params=None, stdin: str = None, check=True, sudo=False) -> str:
        cmd = ["dokku", f"{self.name}:{command}"]
        if params is not None:
            cmd.extend(params)
        return self.dokku._execute(cmd, stdin=stdin, check=check, sudo=sudo)
