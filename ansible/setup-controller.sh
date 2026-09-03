#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly ROOT
readonly SEMAPHORE_ENV_FILE="$ROOT/.semaphore.env"

require_command() {
  command -v "$1" >/dev/null 2>&1
}

usage() {
  cat <<'EOF'
Usage:
  ./setup-controller.sh [--with-semaphore]

Options:
  --with-semaphore  Install Docker/Compose, create Semaphore secrets, and start
                    PostgreSQL + Semaphore UI on port 3000.
EOF
}

with_semaphore=0
for arg in "$@"; do
  case "$arg" in
    --with-semaphore)
      with_semaphore=1
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: Unknown option: %s\n' "$arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! require_command pacman; then
  printf '%s\n' "ERROR: setup-controller.sh currently supports Arch/CachyOS controllers with pacman." >&2
  exit 1
fi

controller_packages=(ansible openssh sshpass python)
if (( with_semaphore == 1 )); then
  controller_packages+=(docker docker-compose)
fi

sudo pacman -Syu --needed --noconfirm "${controller_packages[@]}"

install -d -m 0700 "$HOME/.ssh"
if [[ ! -f $HOME/.ssh/id_ed25519 && ! -f $HOME/.ssh/id_rsa ]]; then
  ssh-keygen -t ed25519 -a 64 -f "$HOME/.ssh/id_ed25519" -N ''
fi

chmod 0600 "$HOME/.ssh"/id_* 2>/dev/null || true
chmod 0644 "$HOME/.ssh"/*.pub 2>/dev/null || true

generate_base64_secret() {
  local bytes=$1
  head -c "$bytes" /dev/urandom | base64
}

ensure_semaphore_env() {
  if [[ -f $SEMAPHORE_ENV_FILE ]]; then
    chmod 0600 "$SEMAPHORE_ENV_FILE"
    return
  fi

  umask 077
  {
    printf '%s\n' "SEMAPHORE_DB_USER=semaphore"
    printf '%s\n' "SEMAPHORE_DB_NAME=semaphore"
    printf 'SEMAPHORE_DB_PASS=%s\n' "$(generate_base64_secret 24)"
    printf '%s\n' "SEMAPHORE_ADMIN=admin"
    printf 'SEMAPHORE_ADMIN_PASSWORD=%s\n' "$(generate_base64_secret 24)"
    printf '%s\n' "SEMAPHORE_ADMIN_NAME=CachyFreeze Admin"
    printf '%s\n' "SEMAPHORE_ADMIN_EMAIL=admin@localhost"
    printf 'SEMAPHORE_ACCESS_KEY_ENCRYPTION=%s\n' "$(generate_base64_secret 32)"
    printf '%s\n' "SEMAPHORE_HTTP_PORT=3000"
    printf '%s\n' "TZ=Europe/Warsaw"
  } >"$SEMAPHORE_ENV_FILE"
}

start_semaphore() {
  ensure_semaphore_env
  sudo systemctl enable --now docker.service

  if sudo docker compose version >/dev/null 2>&1; then
    sudo docker compose \
      -p cachy-freeze-semaphore \
      --env-file "$SEMAPHORE_ENV_FILE" \
      -f "$ROOT/docker-compose.semaphore.yml" \
      up -d
    return
  fi

  if require_command docker-compose; then
    sudo docker-compose \
      -p cachy-freeze-semaphore \
      --env-file "$SEMAPHORE_ENV_FILE" \
      -f "$ROOT/docker-compose.semaphore.yml" \
      up -d
    return
  fi

  printf '%s\n' "ERROR: Docker Compose was installed but no compose command was found." >&2
  exit 1
}

if (( with_semaphore == 1 )); then
  start_semaphore
fi

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

if (( with_semaphore == 1 )); then
  printf '%s\n' \
    "" \
    "Semaphore UI is running at http://localhost:3000" \
    "Admin user: admin" \
    "Admin password is stored in $SEMAPHORE_ENV_FILE (mode 0600)." \
    "Open ansible/SEMAPHORE-REHBERI.md for the CachyFreeze templates."
fi
