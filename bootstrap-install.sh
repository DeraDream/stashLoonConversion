#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/DeraDream/stashLoonConversion.git}"
BIN_LINK="/usr/local/bin/stashloon"
APP_MENU="/opt/stashloon/app/scripts/stashloon-menu.sh"
INSTALLED_ALREADY="0"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer currently supports Linux VPS only." >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this installer as root or with sudo." >&2
  exit 1
fi

echo "Running environment preflight ..."

install_pkg() {
  local pkg="$1"
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y >/dev/null 2>&1
    apt-get install -y "${pkg}" >/dev/null 2>&1
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y "${pkg}" >/dev/null 2>&1
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    yum install -y "${pkg}" >/dev/null 2>&1
    return
  fi
  if command -v apk >/dev/null 2>&1; then
    apk add --no-cache "${pkg}" >/dev/null 2>&1
    return
  fi
  echo "No supported package manager found. Please install ${pkg} manually." >&2
  exit 1
}

if ! command -v git >/dev/null 2>&1; then
  echo "git not found, installing ..."
  install_pkg git
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found, installing ..."
  install_pkg python3
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found, attempting to install systemd ..."
  install_pkg systemd
fi

if [[ -x "${BIN_LINK}" ]] || [[ -x "${APP_MENU}" ]]; then
  echo "Detected existing installation, preparing latest menu ..."
  INSTALLED_ALREADY="1"
fi

TEMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

echo "Cloning ${REPO_URL} ..."
git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/repo" >/dev/null 2>&1

cd "${TEMP_DIR}/repo"
if [[ "${INSTALLED_ALREADY}" == "1" ]]; then
  exec bash scripts/stashloon-menu.sh
fi

exec bash install.sh
