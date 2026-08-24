#!/usr/bin/env bash
set -Eeuo pipefail

export PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/sbin
unset CDPATH ENV BASH_ENV PYTHONHOME PYTHONPATH

INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly INSTALLER_DIR

(( EUID == 0 )) || {
  printf '%s\n' "ERROR: Administrator authorization is required." >&2
  exit 1
}
IFS= read -r boot_secret || {
  printf '%s\n' "ERROR: The boot-maintenance password was not received." >&2
  exit 1
}
(( ${#boot_secret} >= 12 && ${#boot_secret} <= 256 )) || {
  printf '%s\n' "ERROR: The boot-maintenance password must contain 12-256 characters." >&2
  exit 1
}
[[ $boot_secret != *:* && $boot_secret != *$'\r'* && $boot_secret != *$'\n'* ]] || {
  printf '%s\n' "ERROR: The boot-maintenance password contains an unsupported character." >&2
  exit 1
}

command -v pacman >/dev/null || {
  printf '%s\n' "ERROR: CachyFreeze requires CachyOS/Arch Linux with pacman." >&2
  exit 1
}

# Dependency installation is still a system mutation, so first reject every
# unsupported platform/layout condition that can be established with base Arch
# tools. The engine repeats deeper validation after required tools are present.
grep -Eq '^(ID|ID_LIKE)=.*\b(arch|cachyos)\b' /etc/os-release || {
  printf '%s\n' "ERROR: Only CachyOS/Arch Linux is supported." >&2
  exit 1
}
[[ -d /sys/firmware/efi ]] || {
  printf '%s\n' "ERROR: UEFI boot is required." >&2
  exit 1
}
[[ $(findmnt -n -o FSTYPE /) == btrfs ]] || {
  printf '%s\n' "ERROR: The root filesystem is not Btrfs." >&2
  exit 1
}
[[ $(findmnt -n -o SOURCE /) == *'[/@]' ]] || {
  printf '%s\n' "ERROR: Installation requires the persistent THAWED @ root." >&2
  exit 1
}
[[ $(findmnt -n -o TARGET --target /boot) == / ]] || {
  printf '%s\n' "ERROR: A separate /boot filesystem is unsupported." >&2
  exit 1
}
[[ -d /boot/grub && -d /boot/efi/EFI ]] || {
  printf '%s\n' "ERROR: The supported GRUB and /boot/efi layout was not found." >&2
  exit 1
}
[[ $(findmnt -n -o TARGET --target /boot/efi) == /boot/efi &&
  $(findmnt -n -o FSTYPE --target /boot/efi) == vfat ]] || {
  printf '%s\n' "ERROR: The EFI System Partition must be mounted as vfat at /boot/efi." >&2
  exit 1
}
pacman -S --needed --noconfirm btrfs-progs grub mkinitcpio polkit python python-pyqt6
printf '%s\n' "$boot_secret" |
  bash "$INSTALLER_DIR/install-freeze-engine.sh"
unset boot_secret

# Initial Golden is created only from the verified persistent THAWED @. The
# engine stages and validates it before scheduling FROZEN.
if ! /usr/local/sbin/cachy-freeze freeze >/dev/null; then
  printf '%s\n' \
    "ERROR: The core and GRUB authorization were installed, but the initial Golden transaction did not report completion." \
    "No reboot was requested. Run the installer again to reconcile the durable transaction safely." >&2
  exit 1
fi

printf '%s\n' \
  "CachyFreeze was installed and verified." \
  "The initial Golden baseline is ready and FROZEN is scheduled." \
  "The installer will not reboot automatically."
