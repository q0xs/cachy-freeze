#!/usr/bin/env bash
set -Eeuo pipefail

ANSIBLE_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly ANSIBLE_ROOT
PROJECT_ROOT=$(cd -- "$ANSIBLE_ROOT/.." && pwd)
readonly PROJECT_ROOT

command -v ansible-playbook >/dev/null 2>&1 || {
  printf '%s\n' "ERROR: ansible-playbook was not found. Install Ansible first." >&2
  exit 1
}

export ANSIBLE_CONFIG="$ANSIBLE_ROOT/ansible.cfg"
cd "$PROJECT_ROOT"
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/*.yml --syntax-check
