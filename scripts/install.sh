#!/usr/bin/env bash
set -euo pipefail

resolve_script_dir() {
  local source_path="$1"
  while [[ -L "${source_path}" ]]; do
    local source_dir
    source_dir="$(cd -P "$(dirname "${source_path}")" && pwd)"
    source_path="$(readlink "${source_path}")"
    [[ "${source_path}" != /* ]] && source_path="${source_dir}/${source_path}"
  done
  cd -P "$(dirname "${source_path}")" && pwd
}

SCRIPT_DIR="$(resolve_script_dir "${BASH_SOURCE[0]}")"
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
