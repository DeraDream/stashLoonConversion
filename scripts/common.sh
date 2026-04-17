#!/usr/bin/env bash
set -euo pipefail

APP_NAME="stashloon"
SERVICE_NAME="stashloon"
INSTALL_ROOT="/opt/stashloon"
APP_DIR="${INSTALL_ROOT}/app"
CONFIG_DIR="/etc/stashloon"
ENV_FILE="${CONFIG_DIR}/stashloon.env"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
BIN_LINK="/usr/local/bin/stashloon"
DEFAULT_REPO_URL="https://github.com/DeraDream/stashLoonConversion.git"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

color() {
  local code="$1"
  shift
  printf "\033[%sm%s\033[0m\n" "$code" "$*"
}

info() {
  color "1;34" "$*"
}

success() {
  color "1;32" "$*"
}

warn() {
  color "1;33" "$*"
}

error() {
  color "1;31" "$*" >&2
}

is_installed() {
  [[ -f "${APP_DIR}/server.py" ]] && [[ -f "${SERVICE_FILE}" ]]
}

require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    error "该安装器当前面向 Linux VPS。macOS 本地运行请直接使用项目目录。"
    exit 1
  fi
}

ensure_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    error "请使用 root 运行，或在命令前加 sudo。"
    exit 1
  fi
}

ensure_dependencies() {
  local missing=()
  for cmd in bash python3 systemctl install cp rm mkdir ln sed awk git; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if ((${#missing[@]})); then
    error "缺少依赖命令: ${missing[*]}"
    exit 1
  fi
}

ensure_config_file() {
  mkdir -p "${CONFIG_DIR}"
  if [[ ! -f "${ENV_FILE}" ]]; then
    cat >"${ENV_FILE}" <<'EOF'
HOST=0.0.0.0
PORT=8080
PUBLIC_BASE_URL=http://127.0.0.1:8080
SUBSCRIPTION_USERINFO=
REPO_URL=https://github.com/DeraDream/stashLoonConversion.git
EOF
    return
  fi

  if ! grep -q '^REPO_URL=' "${ENV_FILE}"; then
    printf '\nREPO_URL=%s\n' "${DEFAULT_REPO_URL}" >>"${ENV_FILE}"
  fi
}

write_service_file() {
  cat >"${SERVICE_FILE}" <<EOF
[Unit]
Description=StashLoon Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=/usr/bin/python3 ${APP_DIR}/server.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF
}

reload_and_enable_service() {
  systemctl daemon-reload
  systemctl enable --now "${SERVICE_NAME}"
}

restart_service() {
  systemctl restart "${SERVICE_NAME}"
}

stop_disable_service() {
  systemctl disable --now "${SERVICE_NAME}" 2>/dev/null || true
}

install_command_link() {
  mkdir -p "$(dirname "${BIN_LINK}")"
  ln -sf "${APP_DIR}/scripts/stashloon-menu.sh" "${BIN_LINK}"
  chmod +x "${APP_DIR}/scripts/stashloon-menu.sh"
}

copy_project_files() {
  local source_dir="$1"
  mkdir -p "${INSTALL_ROOT}"
  rm -rf "${APP_DIR}.tmp"
  mkdir -p "${APP_DIR}.tmp"
  cp -R "${source_dir}/." "${APP_DIR}.tmp/"
  rm -rf "${APP_DIR}.tmp/data" "${APP_DIR}.tmp/.git" "${APP_DIR}.tmp/.DS_Store"
  if [[ -d "${APP_DIR}" ]]; then
    mkdir -p "${APP_DIR}.tmp/data"
    cp -R "${APP_DIR}/data/." "${APP_DIR}.tmp/data/" 2>/dev/null || true
  fi
  rm -rf "${APP_DIR}"
  mv "${APP_DIR}.tmp" "${APP_DIR}"
}

prepare_source_dir() {
  local repo_url="${REPO_URL:-}"

  if [[ -z "${repo_url}" ]] && [[ -f "${ENV_FILE}" ]]; then
    repo_url="$(
      awk -F= '$1=="REPO_URL" {print substr($0, index($0, "=") + 1)}' "${ENV_FILE}" | tail -n 1
    )"
  fi

  if [[ -z "${repo_url}" ]]; then
    repo_url="${DEFAULT_REPO_URL}"
  fi

  if [[ -n "${repo_url}" ]]; then
    local temp_dir
    temp_dir="$(mktemp -d)"
    info "从 Git 仓库拉取源码: ${repo_url}"
    git clone --depth 1 "${repo_url}" "${temp_dir}/repo" >/dev/null 2>&1
    printf "%s\n" "${temp_dir}/repo"
    return
  fi
  if [[ -f "${PROJECT_ROOT}/server.py" ]]; then
    printf "%s\n" "${PROJECT_ROOT}"
    return
  fi
  error "未找到源码目录。请在项目目录运行，或设置 REPO_URL 后再执行。"
  exit 1
}

print_status() {
  info "安装目录: ${APP_DIR}"
  info "配置文件: ${ENV_FILE}"
  if systemctl is-active --quiet "${SERVICE_NAME}"; then
    success "服务状态: 运行中"
  else
    warn "服务状态: 未运行"
  fi
  if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
    success "开机自启: 已启用"
  else
    warn "开机自启: 未启用"
  fi
}
