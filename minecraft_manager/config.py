import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("MCM_SECRET_KEY", "change-me-before-production")
    DATABASE = os.environ.get("MCM_DATABASE", str(BASE_DIR / "instance" / "manager.sqlite3"))

    SERVER_DIR = Path(os.environ.get("MCM_SERVER_DIR", str(BASE_DIR / "minecraft-server"))).resolve()
    BACKUP_DIR = Path(os.environ.get("MCM_BACKUP_DIR", str(BASE_DIR / "backups"))).resolve()
    SERVICE_NAME = os.environ.get("MCM_SERVICE_NAME", "").strip()
    START_COMMAND = os.environ.get("MCM_START_COMMAND", "").strip()
    STOP_COMMAND = os.environ.get("MCM_STOP_COMMAND", "").strip()
    RESTART_COMMAND = os.environ.get("MCM_RESTART_COMMAND", "").strip()
    UPGRADE_COMMAND = os.environ.get("MCM_UPGRADE_COMMAND", "").strip()

    CONNECTION_HOST = os.environ.get("MCM_CONNECTION_HOST", "example.com")
    CONNECTION_PORT = os.environ.get("MCM_CONNECTION_PORT", "25565")
    SERVER_NAME = os.environ.get("MCM_SERVER_NAME", "Minecraft Server")
    AUTO_WHITELIST_ON_REGISTER = os.environ.get("MCM_AUTO_WHITELIST", "true").lower() == "true"

    VERSION_MANIFEST_URL = os.environ.get(
        "MCM_VERSION_MANIFEST_URL",
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
    )
    PROFILE_URL_TEMPLATE = os.environ.get(
        "MCM_PROFILE_URL_TEMPLATE",
        "https://api.mojang.com/users/profiles/minecraft/{username}",
    )
