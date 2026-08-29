#!/usr/bin/env bash

readonly CWS_LOG_FILE=/var/log/cachy-workstation-setup.log
readonly CWS_LOCK_FILE=/run/lock/cachy-workstation-setup.lock

TARGET_USER=${TARGET_USER:-}
TARGET_UID=${TARGET_UID:-}
TARGET_GID=${TARGET_GID:-}
TARGET_HOME=${TARGET_HOME:-}
TARGET_SHELL=${TARGET_SHELL:-}
TARGET_DESKTOP=${TARGET_DESKTOP:-}
SETUP_MODE=${SETUP_MODE:-install}

timestamp() {
  date --iso-8601=seconds
}

sanitize_log_value() {
  local value=${1:-}
  value=${value//$'\n'/ }
  value=${value//$'\r'/ }
  printf '%s' "$value"
}

log_event() {
  local level=$1 message
  shift
  message=$(sanitize_log_value "$*")
  printf '%s level=%s mode=%s user=%s message=%q\n' \
    "$(timestamp)" "$level" "$SETUP_MODE" "${TARGET_USER:-unresolved}" "$message" >&3
}

info() {
  printf '[i] %s\n' "$*"
  log_event INFO "$*"
}

success() {
  printf '[✓] %s\n' "$*"
  log_event OK "$*"
}

warn() {
  printf '[!] %s\n' "$*" >&2
  log_event WARN "$*"
}

fail() {
  printf '[✗] %s\n' "$*" >&2
  log_event ERROR "$*"
  return 1
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  if [[ -e /proc/self/fd/3 ]]; then
    log_event FATAL "$*"
  fi
  exit 1
}

init_log() {
  local log_parent=${CWS_LOG_FILE%/*}
  install -d -o root -g root -m 0755 "$log_parent"
  [[ ! -L $CWS_LOG_FILE ]] || die "Log path must not be a symbolic link: $CWS_LOG_FILE"
  if [[ ! -e $CWS_LOG_FILE ]]; then
    install -o root -g root -m 0640 /dev/null "$CWS_LOG_FILE"
  fi
  [[ -f $CWS_LOG_FILE ]] || die "Log path is not a regular file: $CWS_LOG_FILE"
  chown root:root "$CWS_LOG_FILE"
  chmod 0640 "$CWS_LOG_FILE"
  exec 3>>"$CWS_LOG_FILE"
}

require_root() {
  (( EUID == 0 )) || die "Run this command as root (for example: sudo ./workstation-setup.sh USER)."
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command is missing: $1"
}

require_supported_os() {
  [[ $(uname -m) == x86_64 ]] || die "Only x86_64 CachyOS/Arch workstations are supported."
  [[ -r /etc/os-release ]] || die "Cannot identify the operating system."

  local id='' id_like=''
  # shellcheck disable=SC1091
  source /etc/os-release
  id=${ID:-}
  id_like=${ID_LIKE:-}
  if [[ $id != cachyos && $id != arch && " $id_like " != *" arch "* ]]; then
    die "This provisioner supports CachyOS/Arch Linux only (detected: ${id:-unknown})."
  fi
}

require_thawed_root() {
  local root_source root_options
  root_source=$(findmnt -n -o SOURCE /) || die "Cannot inspect the root filesystem."
  root_options=$(findmnt -n -o OPTIONS /) || die "Cannot inspect root mount options."

  [[ $root_source == *'[/@]' ]] ||
    die "Provisioning is allowed only from persistent THAWED @; current root is $root_source."
  [[ ,$root_options, == *,rw,* ]] || die "The THAWED root filesystem is read-only."
}

resolve_target_user() {
  local account
  local -a account_fields=()
  [[ $TARGET_USER =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] ||
    die "Invalid target username: $TARGET_USER"

  account=$(getent passwd "$TARGET_USER") || die "User does not exist: $TARGET_USER"
  [[ $(getent passwd "$TARGET_USER" | wc -l) -eq 1 ]] ||
    die "Username resolves to more than one account: $TARGET_USER"
  IFS=: read -r -a account_fields <<<"$account"
  TARGET_UID=${account_fields[2]:-}
  TARGET_GID=${account_fields[3]:-}
  TARGET_HOME=${account_fields[5]:-}
  TARGET_SHELL=${account_fields[6]:-}
  [[ $TARGET_UID =~ ^[0-9]+$ && $TARGET_GID =~ ^[0-9]+$ ]] ||
    die "The target account has invalid numeric identifiers."
  (( TARGET_UID >= 1000 && TARGET_UID < 65534 && TARGET_GID > 0 && TARGET_GID < 65534 )) ||
    die "The target must be a regular non-system account."
  [[ $TARGET_SHELL != */nologin && $TARGET_SHELL != */false ]] ||
    die "The target account does not have an interactive login shell."
  [[ $TARGET_HOME =~ ^/home/[A-Za-z0-9._-]+$ && -d $TARGET_HOME && ! -L $TARGET_HOME ]] ||
    die "The target home must be a conventional real /home/USER directory."
  [[ $(realpath -e -- "$TARGET_HOME") == "$TARGET_HOME" ]] ||
    die "The target home path must not contain symbolic-link components."
  [[ $(stat -c '%u:%g' "$TARGET_HOME") == "$TARGET_UID:$TARGET_GID" ]] ||
    die "The target home owner does not match the account."

  resolve_target_desktop
  readonly TARGET_UID TARGET_GID TARGET_HOME TARGET_SHELL TARGET_DESKTOP
}

validate_target_managed_path() {
  local path=$1 label=${2:-managed user path} normalized
  [[ $path == "$TARGET_HOME/"* ]] || {
    fail "$label must be located below the target home."
    return 1
  }
  [[ $path != *$'\n'* && $path != *$'\r'* ]] || {
    fail "$label contains an invalid control character."
    return 1
  }
  normalized=$(realpath -m -- "$path") || {
    fail "$label cannot be resolved safely."
    return 1
  }
  [[ $normalized == "$path" ]] || {
    fail "$label contains a symbolic-link or non-canonical path component: $path"
    return 1
  }
}

resolve_target_desktop() {
  local candidate=$TARGET_HOME/Desktop
  if [[ -x /usr/bin/xdg-user-dir ]]; then
    local discovered
    discovered=$(run_as_target /usr/bin/xdg-user-dir DESKTOP 2>/dev/null || true)
    if [[ -n $discovered ]]; then
      candidate=$discovered
    fi
  fi
  validate_target_managed_path "$candidate" "XDG desktop directory" || return 1
  TARGET_DESKTOP=$candidate
}

ensure_target_directory() {
  local path=$1 mode=${2:-0755}
  validate_target_managed_path "$path" "Managed target-user directory" || return 1
  if [[ -e $path || -L $path ]]; then
    [[ -d $path && ! -L $path ]] || {
      fail "Managed target-user directory is not a real directory: $path"
      return 1
    }
    chown --no-dereference "$TARGET_UID:$TARGET_GID" "$path" || {
      fail "Could not correct directory ownership: $path"
      return 1
    }
  fi
  run_as_target install -d -m "$mode" -- "$path" || {
    fail "Could not create a target-user directory: $path"
    return 1
  }
  validate_target_managed_path "$path" "Managed target-user directory" || return 1
  [[ $(stat -c '%u:%g' "$path") == "$TARGET_UID:$TARGET_GID" ]] || {
    fail "Managed directory owner is incorrect: $path"
    return 1
  }
}

repair_target_tree_ownership() {
  local path=$1
  validate_target_managed_path "$path" "Managed target-user tree" || return 1
  [[ -d $path && ! -L $path ]] || {
    fail "Managed target-user tree is not a real directory: $path"
    return 1
  }
  find "$path" -xdev -exec chown --no-dereference "$TARGET_UID:$TARGET_GID" {} + || {
    fail "Could not reconcile ownership below: $path"
    return 1
  }
}

user_has_admin_access() {
  local group sudo_listing
  while IFS= read -r group; do
    case $group in
      wheel | sudo | root | admin | docker | lxd)
        return 0
        ;;
    esac
  done < <(id -nG "$TARGET_USER" | tr ' ' '\n')

  if command -v sudo >/dev/null 2>&1; then
    sudo_listing=$(LC_ALL=C sudo -n -ll -U "$TARGET_USER" </dev/null 2>/dev/null || true)
    if grep -q '^Sudoers entry:' <<<"$sudo_listing"; then
      return 0
    fi
  fi
  return 1
}

require_standard_user() {
  user_has_admin_access &&
    die "Target user has sudo, an administrative group, or equivalent host-level access."
  success "Standard-user permission check passed"
}

run_as_target() {
  runuser -u "$TARGET_USER" -- \
    env -i \
    HOME="$TARGET_HOME" \
    USER="$TARGET_USER" \
    LOGNAME="$TARGET_USER" \
    PATH=/usr/local/bin:/usr/bin:/usr/sbin \
    XDG_CONFIG_HOME="$TARGET_HOME/.config" \
    XDG_DATA_HOME="$TARGET_HOME/.local/share" \
    XDG_CACHE_HOME="$TARGET_HOME/.cache" \
    "$@"
}

run_logged() {
  "$@" \
    > >(tee -a "$CWS_LOG_FILE") \
    2> >(tee -a "$CWS_LOG_FILE" >&2)
}

download_https() {
  local url=$1 destination=$2 temporary
  [[ $url == https://* ]] || fail "Only HTTPS downloads are allowed: $url"
  [[ $destination == /* ]] || fail "Download destination must be absolute."
  temporary="${destination}.download.$$"
  rm -f -- "$temporary"
  if ! curl \
    --fail \
    --location \
    --proto '=https' \
    --tlsv1.2 \
    --retry 5 \
    --retry-all-errors \
    --retry-delay 2 \
    --connect-timeout 20 \
    --max-time 900 \
    --output "$temporary" \
    "$url"; then
    rm -f -- "$temporary"
    fail "Download failed: $url"
    return 1
  fi
  [[ -s $temporary ]] || {
    rm -f -- "$temporary"
    fail "Downloaded file is empty: $url"
    return 1
  }
  mv -f -- "$temporary" "$destination"
}

acquire_setup_lock() {
  install -d -o root -g root -m 0755 "${CWS_LOCK_FILE%/*}"
  exec 8>"$CWS_LOCK_FILE"
  flock -n 8 || die "Another workstation setup process is already running."
}
