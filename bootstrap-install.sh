#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/DeraDream/stashLoonConversion.git}"
BIN_LINK="/usr/local/bin/stashloon"
APP_MENU="/opt/stashloon/app/scripts/stashloon-menu.sh"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer currently supports Linux VPS only." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required but not installed." >&2
  exit 1
fi

if [[ -x "${BIN_LINK}" ]]; then
  echo "Detected existing installation, opening menu ..."
  exec "${BIN_LINK}"
fi

if [[ -x "${APP_MENU}" ]]; then
  echo "Detected existing installation, opening menu ..."
  exec "${APP_MENU}"
fi

TEMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

echo "Cloning ${REPO_URL} ..."
git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/repo" >/dev/null 2>&1

cd "${TEMP_DIR}/repo"
exec bash install.sh
