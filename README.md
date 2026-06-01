# MineCraftManager

A small Flask control panel for a private Minecraft server.

## Features

- User registration and login with hashed passwords.
- First registered account becomes the initial admin.
- Registered Minecraft usernames are added to `whitelist.json`.
- Players can see server status, installed version, latest release, and connection details.
- Admins can grant admin access, manage whitelist entries, start/stop/restart the server, and create tar backups.
- Admin forms include CSRF protection.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` for your server paths and connection details. For local development:

```bash
set -a
. ./.env
set +a
flask --app run run --host 0.0.0.0 --port 8080
```

For production, set a real `MCM_SECRET_KEY` and run the app through Gunicorn/systemd:

```bash
.venv/bin/pip install -r requirements.txt
./scripts/install-web-service.sh
sudo systemctl start minecraft-manager.service
systemctl status minecraft-manager.service
```

The installer binds Gunicorn to `0.0.0.0:8080` by default. Override with `MCM_WEB_BIND`, for example:

```bash
MCM_WEB_BIND=127.0.0.1:8080 ./scripts/install-web-service.sh
```

Use a reverse proxy such as nginx or Caddy in front of it when exposing it publicly.

## Minecraft Server Control

The cleanest control path is a systemd unit:

```ini
[Unit]
Description=Minecraft Server
After=network.target

[Service]
WorkingDirectory=/opt/minecraft/server
ExecStart=/usr/bin/java -Xmx2G -Xms1G -jar server.jar nogui
Restart=on-failure
User=minecraft

[Install]
WantedBy=multi-user.target
```

Then set:

```bash
MCM_SERVICE_NAME=minecraft.service
```

If the Flask app runs as a non-root user, grant only the needed service commands through sudoers instead of giving broad sudo access.

This repo includes a ready-to-install unit at `systemd/minecraft.service` using:

```bash
java -Xmx2G -Xms2G -jar /opt/minecraft/server/server.jar nogui
```

It also includes `systemd/minecraft-manager-sudoers`, which lets the Flask process run only the required start, stop, and restart commands through `sudo`.

Install both with:

```bash
chmod +x scripts/install-minecraft-service.sh
./scripts/install-minecraft-service.sh
```

## Upgrade Strategy

This app intentionally does not download and replace your server jar by default. Different servers use different distributions such as Vanilla, Fabric, Paper, or Forge. Put your tested upgrade script in `MCM_UPGRADE_COMMAND`. The admin upgrade button stops the server, creates a backup, runs that command, then starts the server.
