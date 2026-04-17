#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# 优先读取项目内 .env，避免受到外部 shell 里遗留的 HOST/PUBLIC_BASE_URL 干扰
if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

PORT="${PORT:-8080}"
HOST="0.0.0.0"

if [[ -z "${PUBLIC_BASE_URL:-}" ]]; then
  LOCAL_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "$LOCAL_IP" ]]; then
    LOCAL_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [[ -z "$LOCAL_IP" ]]; then
    LOCAL_IP="127.0.0.1"
  fi
  export PUBLIC_BASE_URL="http://${LOCAL_IP}:${PORT}"
fi

export HOST
export PORT

echo "Starting StashAndLoon"
echo "Bind:    ${HOST}:${PORT}"
echo "Local:   http://127.0.0.1:${PORT}"
echo "LAN:     ${PUBLIC_BASE_URL}"
echo "Press Ctrl+C to stop"

exec python3 server.py
