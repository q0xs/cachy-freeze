#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly ROOT

require_command() {
  command -v "$1" >/dev/null 2>&1
}

if ! require_command pacman; then
  printf '%s\n' "ERROR: setup-controller.sh currently supports Arch/CachyOS controllers with pacman." >&2
  exit 1
fi

sudo pacman -Syu --needed --noconfirm ansible openssh sshpass python

install -d -m 0700 "$HOME/.ssh"
if [[ ! -f $HOME/.ssh/id_ed25519 && ! -f $HOME/.ssh/id_rsa ]]; then
  ssh-keygen -t ed25519 -a 64 -f "$HOME/.ssh/id_ed25519" -N ''
fi

chmod 0600 "$HOME/.ssh"/id_* 2>/dev/null || true
chmod 0644 "$HOME/.ssh"/*.pub 2>/dev/null || true

printf '%s\n' \
  "CachyFreeze Ansible controller is ready." \
  "" \
  "1. Edit inventory/hosts.ini and set employee_user for each host." \
  "2. Copy this controller SSH key to LocalAdm on each target, for example:" \
  "   ssh-copy-id LocalAdm@192.0.2.10" \
  "" \
  "Lab syntax check:" \
  "   cd $ROOT && ansible-playbook playbooks/status.yml --syntax-check" \
  "" \
  "Provision a lab batch:" \
  "   cd $ROOT && ansible-playbook playbooks/provision.yml --limit lab --ask-become-pass --ask-vault-pass" \
  "" \
  "Maintenance:" \
  "   cd $ROOT && ansible-playbook playbooks/maintenance.yml --limit lab"
