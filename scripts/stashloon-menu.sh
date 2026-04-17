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

menu_install() {
  if is_installed; then
    warn "已安装，返回菜单。"
    return
  fi
  "${SCRIPT_DIR}/install.sh"
}

menu_update() {
  require_linux
  ensure_root
  ensure_dependencies
  if ! is_installed; then
    warn "尚未安装，请先执行安装。"
    return
  fi

  local source_dir
  source_dir="$(prepare_source_dir)"
  info "开始更新 ${APP_NAME}..."
  copy_project_files "${source_dir}"
  ensure_config_file
  write_service_file
  install_command_link
  reload_and_enable_service
  success "更新完成。"
}

menu_restart() {
  require_linux
  ensure_root
  if ! is_installed; then
    warn "尚未安装，无法重启。"
    return
  fi
  restart_service
  success "服务已重启。"
}

menu_uninstall() {
  require_linux
  ensure_root
  if ! is_installed; then
    warn "当前未安装。"
    return
  fi

  if ! prompt_input "确认卸载 ${APP_NAME} 吗？这会删除程序文件，但保留 ${CONFIG_DIR} 配置。 [y/N] " answer; then
    warn "未读取到确认输入，已取消卸载。"
    return
  fi
  if [[ ! "${answer}" =~ ^[Yy]$ ]]; then
    warn "已取消卸载。"
    return
  fi

  stop_disable_service
  rm -f "${SERVICE_FILE}" "${BIN_LINK}"
  rm -rf "${INSTALL_ROOT}"
  systemctl daemon-reload
  success "卸载完成。"
}

menu_status() {
  require_linux
  ensure_root
  if ! is_installed; then
    warn "当前未安装。"
    return
  fi
  print_status
  systemctl --no-pager --full status "${SERVICE_NAME}" || true
}

show_menu() {
  while true; do
    printf "\n"
    info "========== StashLoon 菜单 =========="
    info "面板地址: $(get_panel_url)"
    printf "1. 安装\n"
    printf "2. 更新\n"
    printf "3. 重启\n"
    printf "4. 卸载\n"
    printf "5. 状态\n"
    printf "0. 退出\n"
    if ! prompt_input "请选择操作: " choice; then
      warn "未检测到可交互终端，退出菜单。"
      exit 0
    fi
    case "${choice}" in
      1) menu_install ;;
      2) menu_update ;;
      3) menu_restart ;;
      4) menu_uninstall ;;
      5) menu_status ;;
      0) exit 0 ;;
      *) warn "无效选项，请重新输入。" ;;
    esac
  done
}

show_menu
