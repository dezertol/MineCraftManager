import os
import shlex
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if value:
            try:
                parsed = shlex.split(value, comments=False, posix=True)
                value = parsed[0] if len(parsed) == 1 else value
            except ValueError:
                value = value.strip("\"'")

        os.environ[key] = value
