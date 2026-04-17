#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

run_install() {
  require_linux
  ensure_root
  ensure_dependencies

  if is_installed; then
    warn "检测到 ${APP_NAME} 已安装，直接打开菜单。"
    exec "${APP_DIR}/scripts/stashloon-menu.sh"
  fi

  local source_dir
  source_dir="$(prepare_source_dir)"

  info "开始安装 ${APP_NAME}..."
  mkdir -p "${INSTALL_ROOT}"
  copy_project_files "${source_dir}"
  ensure_config_file
  local panel_url
  panel_url="$(configure_panel_address)"
  write_service_file
  install_command_link
  reload_and_enable_service

  success "安装完成。"
  success "面板地址: ${panel_url}"
  print_status
  info "现在可以直接运行命令: stashloon"
  exec "${APP_DIR}/scripts/stashloon-menu.sh"
}

run_install "$@"
