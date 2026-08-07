#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly TEST_ROOT=$(mktemp -d /tmp/cachy-freeze-users.XXXXXX)
readonly TEST_USER="cfstest$$"

cleanup() {
  if [[ $TEST_USER == cfstest+([0-9]) ]]; then
    userdel --remove "$TEST_USER" >/dev/null 2>&1 || true
    groupdel "$TEST_USER" >/dev/null 2>&1 || true
  fi
  rm -rf --one-file-system "$TEST_ROOT"
}

fail() {
  printf 'TEST HATASI: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || fail "Kullanıcı entegrasyon testi root gerektirir."
shopt -s extglob
trap cleanup EXIT

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
)

created = manager.create(username, "CachyFreeze Test", "Test-Password-42")
assert created["administrator"] is False
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
assert (root / "templates" / username).is_dir()
PY

test_home=$(getent passwd "$TEST_USER" | cut -d: -f6)
printf '%s\n' transient >"$test_home/frozen-change"
CACHY_USER_TEMPLATE_ROOT="$TEST_ROOT/templates" \
  "$PROJECT_ROOT/user/files/cachy-employee-reset"
[[ ! -e $test_home/frozen-change ]] ||
  fail "Yönetilen standart kullanıcı ev şablonuna sıfırlanmadı."

if id "$TEST_USER" >/dev/null 2>&1; then
  runuser -u "$TEST_USER" -- env \
    PYTHONPATH="$PROJECT_ROOT/src" \
    CACHY_FREEZE_CONFIG="$PROJECT_ROOT/deepfreeze/etc/cachy-freeze.conf" \
    python -m cachy_freeze.cli status >/dev/null 2>&1 &&
    fail "Standart kullanıcı ayrıcalıklı backend komutunu çalıştırabildi."
fi

printf '%s\n' "Kullanıcı ve yetki entegrasyon testleri başarılı."
