#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    line="${raw_line#"${raw_line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "${line:0:1}" == "#" || "$line" != *"="* ]] && continue

    key="${line%%=*}"
    value="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    [[ -n "${!key-}" ]] && continue

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "$key=$value"
  done < .env
fi

SERVICE_NAME="${MCM_SERVICE_NAME:-minecraft.service}"
SERVICE_USER="${MCM_SERVICE_USER:-${SUDO_USER:-$USER}}"
SERVICE_GROUP="${MCM_SERVICE_GROUP:-$(id -gn "$SERVICE_USER")}"
SERVER_DIR="${MCM_SERVER_DIR:-/opt/minecraft/server}"
SERVER_JAR="${MCM_SERVER_JAR:-$SERVER_DIR/server.jar}"
JAVA_BIN="${JAVA_BIN:-$(command -v java || true)}"
XMS="${MCM_XMS:-2G}"
XMX="${MCM_XMX:-2G}"
SYSTEMCTL_BIN="$(command -v systemctl)"

if [[ -z "$JAVA_BIN" ]]; then
  echo "java was not found. Install Java first, then rerun this script." >&2
  exit 1
fi

if [[ ! -f "$SERVER_JAR" ]]; then
  echo "Minecraft server jar was not found: $SERVER_JAR" >&2
  exit 1
fi

service_file="$(mktemp)"
sudoers_file="$(mktemp)"
trap 'rm -f "$service_file" "$sudoers_file"' EXIT

cat > "$service_file" <<UNIT
[Unit]
Description=Minecraft Server
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$SERVER_DIR
ExecStart=$JAVA_BIN -Xmx$XMX -Xms$XMS -jar $SERVER_JAR nogui
Restart=on-failure
RestartSec=10
SuccessExitStatus=0 143
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
UNIT

cat > "$sudoers_file" <<SUDOERS
# Allows the web app user to control only the Minecraft service without a password.
$SERVICE_USER ALL=(root) NOPASSWD: $SYSTEMCTL_BIN start $SERVICE_NAME, $SYSTEMCTL_BIN stop $SERVICE_NAME, $SYSTEMCTL_BIN restart $SERVICE_NAME
SUDOERS

sudo install -m 0644 "$service_file" "/etc/systemd/system/$SERVICE_NAME"
sudo install -m 0440 "$sudoers_file" /etc/sudoers.d/minecraft-manager
sudo visudo -cf /etc/sudoers.d/minecraft-manager
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "Installed $SERVICE_NAME."
echo "User: $SERVICE_USER"
echo "Command: $JAVA_BIN -Xmx$XMX -Xms$XMS -jar $SERVER_JAR nogui"
echo "Use: sudo systemctl start $SERVICE_NAME"
echo "Use: systemctl status $SERVICE_NAME"
