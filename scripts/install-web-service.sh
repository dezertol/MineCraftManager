#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

SERVICE_NAME="${MCM_WEB_SERVICE_NAME:-minecraft-manager.service}"
SERVICE_USER="${MCM_WEB_SERVICE_USER:-${SUDO_USER:-$USER}}"
SERVICE_GROUP="${MCM_WEB_SERVICE_GROUP:-$(id -gn "$SERVICE_USER")}"
APP_DIR="$(pwd)"
ENV_FILE="$APP_DIR/.env"
BIND="${MCM_WEB_BIND:-0.0.0.0:8080}"
WORKERS="${MCM_WEB_WORKERS:-2}"
GUNICORN_BIN="$APP_DIR/.venv/bin/gunicorn"

if [[ ! -x "$GUNICORN_BIN" ]]; then
  echo "Gunicorn was not found at $GUNICORN_BIN" >&2
  echo "Run: .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env was not found at $ENV_FILE" >&2
  exit 1
fi

service_file="$(mktemp)"
trap 'rm -f "$service_file"' EXIT

cat > "$service_file" <<UNIT
[Unit]
Description=Minecraft Manager Web App
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$GUNICORN_BIN --workers $WORKERS --bind $BIND run:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo install -m 0644 "$service_file" "/etc/systemd/system/$SERVICE_NAME"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "Installed $SERVICE_NAME."
echo "Use: sudo systemctl start $SERVICE_NAME"
echo "Use: systemctl status $SERVICE_NAME"
