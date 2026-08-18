#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly PROJECT_ROOT
TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-users.XXXXXX)
readonly TEST_ROOT
readonly TEST_USER="cfstest$$"
readonly TEST_PROVISIONER=$TEST_ROOT/prepare-standard-user.sh

cleanup() {
  local cleanup_failed=0
  if [[ $TEST_USER == cfstest+([0-9]) ]]; then
    loginctl terminate-user "$TEST_USER" >/dev/null 2>&1 || true
    userdel --force --remove "$TEST_USER" >/dev/null 2>&1 || cleanup_failed=1
    groupdel "$TEST_USER" >/dev/null 2>&1 || true
    id "$TEST_USER" >/dev/null 2>&1 && cleanup_failed=1
  fi
  rm -rf --one-file-system "$TEST_ROOT"
  return "$cleanup_failed"
}

fail() {
  printf 'TEST ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || fail "The user integration test requires root."
shopt -s extglob
trap cleanup EXIT
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' >"$TEST_PROVISIONER"
chmod 0755 "$TEST_PROVISIONER"

PYTHONPATH="$PROJECT_ROOT/src" python - "$TEST_ROOT" "$TEST_USER" <<'PY'
import sys
from pathlib import Path

from cachy_freeze.catalog import AuditLogger
from cachy_freeze.runner import CommandRunner
from cachy_freeze.users import UserManager

root = Path(sys.argv[1])
username = sys.argv[2]
manager = UserManager(
    state_dir=root / "state",
    lock_file=root / "user.lock",
    logger=AuditLogger(root / "audit.jsonl"),
    runner=CommandRunner(),
    autologin_path=root / "sddm.conf",
    template_root=root / "templates",
    provisioner_path=root / "prepare-standard-user.sh",
)

created = manager.create(username, "CachyFreeze Test", "Test-Password-42")
assert created["administrator"] is False
created_groups = set(created["groups"])
assert username in created_groups
assert not {"wheel", "sudo"}.intersection(created_groups)
assert (root / "templates" / username).is_dir()
manager.set_locked(username, True)
assert next(item for item in manager.list_users() if item["username"] == username)["locked"]
manager.set_locked(username, False)
manager.set_autologin(username)
assert next(item for item in manager.list_users() if item["username"] == username)["autologin"]
deleted = manager.delete(username)
assert deleted["backup_id"].endswith(username)
restored = manager.restore(deleted["backup_id"])
assert restored["username"] == username
assert restored["administrator"] is False
assert set(restored["groups"]) == created_groups
assert (root / "templates" / username).is_dir()
PY

test_home=$(getent passwd "$TEST_USER" | cut -d: -f6)
printf '%s\n' transient >"$test_home/frozen-change"
CACHY_USER_TEMPLATE_ROOT="$TEST_ROOT/templates" \
  "$PROJECT_ROOT/user/files/cachy-employee-reset"
[[ ! -e $test_home/frozen-change ]] ||
  fail "The managed standard user was not reset to its home template."

if id "$TEST_USER" >/dev/null 2>&1; then
  runuser -u "$TEST_USER" -- env \
    PYTHONPATH="$PROJECT_ROOT/src" \
    CACHY_FREEZE_CONFIG="$PROJECT_ROOT/deepfreeze/etc/cachy-freeze.conf" \
    python -m cachy_freeze.cli status >/dev/null 2>&1 &&
    fail "A standard user could run a privileged backend command."
fi

printf '%s\n' "User and privilege integration tests passed."
