#!/usr/bin/env bash
set -euo pipefail

# One-command deploy for Ubuntu 24.04+
# Usage:
#   sudo REPO_URL="https://github.com/ZentifyID/schedule-bot.git" bash deploy_ubuntu.sh
#
# Optional env vars:
#   APP_DIR=/opt/schedule-bot
#   BRANCH=main
#   RUN_USER=root
#   GROUP_NAME="31 ИС"

REPO_URL="${REPO_URL:-https://github.com/ZentifyID/schedule-bot.git}"
APP_DIR="${APP_DIR:-/opt/schedule-bot}"
BRANCH="${BRANCH:-main}"
RUN_USER="${RUN_USER:-root}"
GROUP_NAME="${GROUP_NAME:-31 ИС}"
SERVICE_NAME="schedule-bot"
ENV_FILE="$APP_DIR/.env"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[1/7] Installing system packages..."
apt update
apt install -y git python3 python3-venv curl jq

echo "[2/7] Cloning/updating repository..."
if [[ ! -d "$APP_DIR/.git" ]]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "[3/7] Preparing virtual environment..."
python3 -m venv .venv

echo "[4/7] Checking .env..."
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<'EOF'
TELEGRAM_BOT_TOKEN=
YANDEX_PUBLIC_URL=https://disk.yandex.ru/d/F_GFm6_Qi9GYAQ
TARGET_GROUP=31 ИС
BOT_TIMEZONE=Europe/Saratov
WEEK1_START_DATE=
TELEGRAM_THREAD_ID=
AUTO_POST_ENABLED=true
AUTO_POST_CHAT_ID=
AUTO_POST_THREAD_ID=
AUTO_POST_INTERVAL_MIN=60
AUTO_POST_STATE_FILE=/opt/schedule-bot/.auto_post_state.json
EOF
  chmod 600 "$ENV_FILE"
  echo
  echo "Created $ENV_FILE. Fill required values and run again:"
  echo "  - TELEGRAM_BOT_TOKEN"
  echo "  - AUTO_POST_CHAT_ID"
  echo "  - AUTO_POST_THREAD_ID"
  exit 1
fi
chmod 600 "$ENV_FILE"

echo "[5/7] Writing systemd service..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Schedule Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/main.py run-bot --base $APP_DIR/schedule.base.json --group "$GROUP_NAME"
Restart=always
RestartSec=5
User=$RUN_USER

[Install]
WantedBy=multi-user.target
EOF

echo "[6/7] Reloading and restarting service..."
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "[7/7] Done. Current status:"
systemctl --no-pager --full status "$SERVICE_NAME" || true
echo
echo "Logs:"
echo "  journalctl -u $SERVICE_NAME -f"
