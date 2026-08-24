#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly ROOT
WORK=$(mktemp -d /tmp/cachy-freeze-grub-vm.XXXXXX)
readonly WORK
readonly TEST_USER=cachyadmin
readonly TEST_PASSWORD='VmTest-Only-123!'

fail() {
  printf 'VM TEST ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  rm -rf --one-file-system "$WORK"
}
trap cleanup EXIT

for command in expect grub-mkpasswd-pbkdf2 grub-mkstandalone qemu-system-x86_64; do
  command -v "$command" >/dev/null || fail "Required command is missing: $command"
done

ovmf_code=
ovmf_vars=
for candidate in \
  /usr/share/OVMF/OVMF_CODE.fd \
  /usr/share/OVMF/OVMF_CODE_4M.fd \
  /usr/share/edk2/x64/OVMF_CODE.fd \
  /usr/share/edk2/x64/OVMF_CODE.4m.fd \
  /usr/share/edk2-ovmf/x64/OVMF_CODE.fd; do
  if [[ -r $candidate ]]; then
    ovmf_code=$candidate
    break
  fi
done
for candidate in \
  /usr/share/OVMF/OVMF_VARS.fd \
  /usr/share/OVMF/OVMF_VARS_4M.fd \
  /usr/share/edk2/x64/OVMF_VARS.fd \
  /usr/share/edk2/x64/OVMF_VARS.4m.fd \
  /usr/share/edk2-ovmf/x64/OVMF_VARS.fd; do
  if [[ -r $candidate ]]; then
    ovmf_vars=$candidate
    break
  fi
done
[[ -n $ovmf_code && -n $ovmf_vars ]] || fail "OVMF firmware files were not found."

password_hash=$(LC_ALL=C printf '%s\n%s\n' "$TEST_PASSWORD" "$TEST_PASSWORD" |
  grub-mkpasswd-pbkdf2 2>/dev/null |
  sed -n 's/^PBKDF2 hash of your password is //p')
[[ $password_hash == grub.pbkdf2.* ]] || fail "The test-only GRUB hash was not generated."

build_case() {
  local mode=$1 case_root=$2
  local boot_dir=$case_root/boot-files fake_bin=$case_root/bin
  local generated=$case_root/generated.cfg config=$case_root/grub.cfg
  install -d -m 0755 "$boot_dir" "$fake_bin" "$case_root/esp/EFI/BOOT"
  touch "$boot_dir/vmlinuz-linux-cachyos" "$boot_dir/initramfs-linux-cachyos.img"
  cat >"$fake_bin/findmnt" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '11111111-2222-3333-4444-555555555555'
EOF
  chmod 0755 "$fake_bin/findmnt"

  PATH="$fake_bin:$PATH" \
    CACHY_FREEZE_CONFIG="$ROOT/etc/cachy-freeze.conf" \
    CACHY_FREEZE_BOOT_DIR="$boot_dir" \
    "$ROOT/grub/99_cachy_freeze" >"$generated"

  cat >"$config" <<EOF
serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1
terminal_input serial
terminal_output serial
set timeout=0
set default=0
set pager=0
set superusers="$TEST_USER"
password_pbkdf2 $TEST_USER $password_hash
set cachy_mode="$mode"
set cachy_recovery="0"
echo CACHY_GRUB_READY
EOF
  sed \
    -e '/^[[:space:]]*insmod gzio$/,/^[[:space:]]*initrd /c\        echo CACHY_PROTECTED_LOAD_REACHED' \
    -e '$i\    echo CACHY_ENTRY_RETURNED\
    halt' \
    "$generated" >>"$config"

  grub-script-check "$config"
  grub-mkstandalone \
    --format=x86_64-efi \
    --output="$case_root/esp/EFI/BOOT/BOOTX64.EFI" \
    --modules="normal serial terminal password_pbkdf2 echo halt" \
    "boot/grub/grub.cfg=$config"
  cp "$ovmf_vars" "$case_root/OVMF_VARS.fd"
}

run_vm() {
  local case_root=$1 password=$2 expected=$3 transcript=$4
  VM_CASE_ROOT=$case_root \
    VM_OVMF_CODE=$ovmf_code \
    VM_USER=$TEST_USER \
    VM_PASSWORD=$password \
    VM_EXPECTED=$expected \
    VM_TRANSCRIPT=$transcript \
    timeout 90 expect <<'EOF'
set timeout 60
# OVMF's emulated serial input can drop characters while GRUB redraws its
# authentication prompt. Keep every character well outside that window; a
# truncated username can otherwise look like an authorization regression.
set send_slow {1 0.25}
log_file -noappend $env(VM_TRANSCRIPT)
spawn qemu-system-x86_64 \
  -machine q35,accel=tcg \
  -m 256 \
  -no-reboot \
  -nographic \
  -drive if=pflash,format=raw,readonly=on,file=$env(VM_OVMF_CODE) \
  -drive if=pflash,format=raw,file=$env(VM_CASE_ROOT)/OVMF_VARS.fd \
  -drive format=raw,file=fat:rw:$env(VM_CASE_ROOT)/esp
if {$env(VM_PASSWORD) ne ""} {
  expect {
    "Enter username:" {}
    timeout { exit 42 }
    eof { exit 43 }
  }
  after 1500
  send -s -- "$env(VM_USER)"
  after 1000
  send -- "\r"
  expect {
    "Enter password:" {}
    timeout { exit 44 }
    eof { exit 45 }
  }
  after 1500
  send -s -- "$env(VM_PASSWORD)"
  after 1000
  send -- "\r"
}
if {$env(VM_EXPECTED) eq "allowed"} {
  expect {
    "CACHY_PROTECTED_LOAD_REACHED" {}
    timeout { exit 46 }
    eof { exit 47 }
  }
  expect {
    "CACHY_ENTRY_RETURNED" {}
    timeout { exit 48 }
    eof { exit 49 }
  }
} else {
  expect {
    "CACHY_PROTECTED_LOAD_REACHED" { exit 41 }
    "CACHY_ENTRY_RETURNED" {}
    timeout { exit 50 }
    eof { exit 51 }
  }
}
send -- "\001x"
expect {
  eof {}
  timeout { exit 52 }
}
EOF
}

run_case() {
  local name=$1 mode=$2 password=$3 expected=$4
  local case_root=$WORK/$name transcript=
  local attempt=1 max_attempts=1 vm_status=0
  build_case "$mode" "$case_root"

  # OVMF's emulated serial receiver can very rarely drop a hidden password
  # character even with deliberately slow input. Retry only that exact
  # allowed-case denial; a real authentication regression still fails all
  # three fresh-firmware attempts, while denied/passwordless cases never retry.
  if [[ -n $password && $expected == allowed ]]; then
    max_attempts=3
  fi
  while ((attempt <= max_attempts)); do
    transcript=$WORK/$name-attempt-$attempt.log
    cp "$ovmf_vars" "$case_root/OVMF_VARS.fd"
    if run_vm "$case_root" "$password" "$expected" "$transcript"; then
      vm_status=0
      break
    else
      vm_status=$?
    fi
    if ((vm_status != 47 || attempt == max_attempts)); then
      return "$vm_status"
    fi
    printf 'RETRY: %s serial password attempt %d/%d was denied.\n' \
      "$name" "$attempt" "$max_attempts" >&2
    ((attempt += 1))
  done
  ((vm_status == 0)) || return "$vm_status"

  grep -q 'CACHY_GRUB_READY' "$transcript" || fail "$name did not start GRUB."
  if [[ -n $password ]]; then
    grep -q "$TEST_USER" "$transcript" || fail "$name did not receive the complete username."
  fi
  if [[ $expected == denied ]]; then
    ! grep -q 'CACHY_PROTECTED_LOAD_REACHED' "$transcript" ||
      fail "$name reached the protected load marker."
  else
    grep -q 'CACHY_PROTECTED_LOAD_REACHED' "$transcript" ||
      fail "$name did not reach the protected load marker."
  fi
  grep -q 'CACHY_ENTRY_RETURNED' "$transcript" || fail "$name did not finish its entry."
  printf 'PASS: %s\n' "$name"
}

run_case thawed-wrong-password thawed 'definitely-wrong' denied
run_case thawed-correct-password thawed "$TEST_PASSWORD" allowed
run_case frozen-passwordless frozen '' allowed

printf '%s\n' "UEFI GRUB authentication acceptance tests passed in disposable QEMU VMs."
