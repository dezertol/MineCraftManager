import json
import os
import re
import shlex
import subprocess
import tarfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from flask import current_app


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
VERSION_RE = re.compile(r"Starting minecraft server version ([^\s]+)", re.IGNORECASE)


@dataclass
class CommandResult:
    ok: bool
    message: str


def server_dir() -> Path:
    return Path(current_app.config["SERVER_DIR"])


def whitelist_path() -> Path:
    return server_dir() / "whitelist.json"


def validate_minecraft_name(name: str) -> bool:
    return bool(USERNAME_RE.fullmatch(name))


def run_admin_command(action: str) -> CommandResult:
    service = current_app.config["SERVICE_NAME"]
    configured = {
        "start": current_app.config["START_COMMAND"],
        "stop": current_app.config["STOP_COMMAND"],
        "restart": current_app.config["RESTART_COMMAND"],
        "upgrade": current_app.config["UPGRADE_COMMAND"],
    }

    if configured.get(action):
        command = shlex.split(configured[action])
    elif service and action in {"start", "stop", "restart"}:
        command = ["systemctl", action, service]
    else:
        return CommandResult(False, "No service name or command is configured for this action.")

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except FileNotFoundError as exc:
        return CommandResult(False, f"Command not found: {exc.filename}")
    except subprocess.TimeoutExpired:
        return CommandResult(False, "Command timed out.")

    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode == 0:
        return CommandResult(True, output or f"{action.title()} command completed.")
    if "a password is required" in output or "a terminal is required" in output:
        return CommandResult(
            False,
            "sudo is not configured for passwordless Minecraft service control. "
            "Install systemd/minecraft-manager-sudoers with ./scripts/install-minecraft-service.sh.",
        )
    return CommandResult(False, output or f"{action.title()} command failed with exit code {completed.returncode}.")


def status() -> dict:
    service = current_app.config["SERVICE_NAME"]
    running = False
    status_text = "Not configured"

    if service:
        completed = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        running = completed.stdout.strip() == "active"
        status_text = completed.stdout.strip() or completed.stderr.strip() or "unknown"
    else:
        status_text = "Configure MCM_SERVICE_NAME for live systemd status."

    return {
        "running": running,
        "status_text": status_text,
        "version": installed_version(),
        "latest_version": latest_release_version(),
        "connection_host": current_app.config["CONNECTION_HOST"],
        "connection_port": current_app.config["CONNECTION_PORT"],
        "server_dir": str(server_dir()),
    }


def installed_version() -> str:
    version_file = server_dir() / "version.txt"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip() or "Unknown"

    latest_log = server_dir() / "logs" / "latest.log"
    if latest_log.exists():
        for line in reversed(latest_log.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]):
            match = VERSION_RE.search(line)
            if match:
                return match.group(1)

    return "Unknown"


def latest_release_version() -> str:
    try:
        with urllib.request.urlopen(current_app.config["VERSION_MANIFEST_URL"], timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("latest", {}).get("release", "Unavailable")
    except Exception:
        return "Unavailable"


def format_uuid(raw_uuid: str) -> str:
    cleaned = raw_uuid.replace("-", "")
    if len(cleaned) != 32:
        return raw_uuid
    return f"{cleaned[0:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:32]}"


def fetch_profile(username: str) -> dict | None:
    url = current_app.config["PROFILE_URL_TEMPLATE"].format(username=username)
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 204:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            if not payload.get("id") or not payload.get("name"):
                return None
            return {"uuid": format_uuid(payload["id"]), "name": payload["name"]}
    except Exception:
        return None


def load_whitelist() -> list[dict]:
    path = whitelist_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_whitelist(entries: list[dict]) -> None:
    path = whitelist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def add_to_whitelist(username: str) -> CommandResult:
    if not validate_minecraft_name(username):
        return CommandResult(False, "Minecraft usernames must be 3-16 characters: letters, numbers, and underscores.")

    profile = fetch_profile(username)
    if profile is None:
        return CommandResult(False, f"Could not resolve a UUID for {username}. Check the username and API access.")

    entries = load_whitelist()
    if any(item.get("name", "").lower() == username.lower() for item in entries):
        return CommandResult(True, f"{username} is already whitelisted.")

    entries.append(profile)
    save_whitelist(entries)
    return CommandResult(True, f"{profile['name']} was added to whitelist.json.")


def remove_from_whitelist(username: str) -> CommandResult:
    entries = load_whitelist()
    filtered = [item for item in entries if item.get("name", "").lower() != username.lower()]
    if len(filtered) == len(entries):
        return CommandResult(True, f"{username} was not present in whitelist.json.")
    save_whitelist(filtered)
    return CommandResult(True, f"{username} was removed from whitelist.json.")


def make_backup() -> CommandResult:
    source = server_dir()
    if not source.exists():
        return CommandResult(False, f"Server directory does not exist: {source}")

    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = backup_dir / f"minecraft-backup-{stamp}.tar.gz"

    def exclude(tarinfo: tarfile.TarInfo):
        full_path = source.parent / tarinfo.name
        if archive.parent == full_path or archive.parent in full_path.parents:
            return None
        return tarinfo

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(source, arcname=source.name, filter=exclude)

    return CommandResult(True, f"Backup created: {archive}")


def latest_backups(limit: int = 5) -> list[dict]:
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    archives = sorted(backup_dir.glob("minecraft-backup-*.tar.gz"), key=os.path.getmtime, reverse=True)
    return [
        {
            "name": item.name,
            "path": str(item),
            "size": item.stat().st_size,
            "created": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        for item in archives[:limit]
    ]
