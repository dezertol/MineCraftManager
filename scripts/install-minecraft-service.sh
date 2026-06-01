#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

sudo install -m 0644 systemd/minecraft.service /etc/systemd/system/minecraft.service
sudo install -m 0440 systemd/minecraft-manager-sudoers /etc/sudoers.d/minecraft-manager
sudo visudo -cf /etc/sudoers.d/minecraft-manager
sudo systemctl daemon-reload
sudo systemctl enable minecraft.service

echo "Installed minecraft.service."
echo "Use: sudo systemctl start minecraft.service"
echo "Use: systemctl status minecraft.service"
