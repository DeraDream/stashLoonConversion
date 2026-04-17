#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/DeraDream/stashLoonConversion.git}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer currently supports Linux VPS only." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required but not installed." >&2
  exit 1
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
