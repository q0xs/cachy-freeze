#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
version=$(<"$PROJECT_ROOT/VERSION")
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(rc[0-9]+)?$ ]] || {
  printf '%s\n' "ERROR: Invalid VERSION." >&2
  exit 1
}

output_dir=$PROJECT_ROOT/dist
output=$output_dir/CachyFreeze-Installer-$version.run
work=$(mktemp -d)
trap 'rm -rf --one-file-system "$work"' EXIT
install -d "$output_dir"

cat >"$work/header" <<'HEADER'
#!/usr/bin/env bash
set -Eeuo pipefail

show_error() {
  if command -v kdialog >/dev/null 2>&1; then
    kdialog --title "CachyFreeze Installer" --error "$1"
  elif command -v zenity >/dev/null 2>&1; then
    zenity --error --title="CachyFreeze Installer" --text="$1"
  else
    printf 'ERROR: %s\n' "$1" >&2
  fi
}

payload_root=$(mktemp -d "${TMPDIR:-/tmp}/cachyfreeze-installer.XXXXXXXX") || exit 1
cleanup() { rm -rf --one-file-system "$payload_root"; }
trap cleanup EXIT INT TERM
marker_line=$(awk '/^__CACHYFREEZE_PAYLOAD_BELOW__$/ { print NR + 1; exit }' "$0")
[[ $marker_line =~ ^[0-9]+$ ]] || {
  show_error "The installer payload marker is invalid."
  exit 1
}
if ! tail -n +"$marker_line" "$0" | gzip -dc | tar -xf - -C "$payload_root"; then
  show_error "The installer payload is corrupt. Download it again."
  exit 1
fi
expected_manifest_hash=__CACHYFREEZE_MANIFEST_HASH__
manifest=$payload_root/.cachyfreeze-payload.sha256
actual_manifest_hash=$(sha256sum "$manifest" | cut -d' ' -f1)
if [[ $actual_manifest_hash != "$expected_manifest_hash" ]] ||
  ! (cd "$payload_root" && sha256sum --strict -c .cachyfreeze-payload.sha256 >/dev/null); then
  show_error "The installer payload integrity check failed. Download it again."
  exit 1
fi
[[ -x /usr/bin/pkexec ]] || {
  show_error "PolicyKit was not found. A CachyOS KDE installation is required."
  exit 1
}

# Authenticate before the GUI is opened, copy the verified payload into a
# root-owned /run directory, and verify it again after the privilege boundary.
# This prevents a same-user process from replacing the helper while the GUI is
# waiting for the user to start installation.
staged_root=$(
  /usr/bin/pkexec /usr/bin/bash -c '
    set -Eeuo pipefail
    export PATH=/usr/bin:/usr/sbin
    source_root=$1
    expected_hash=$2
    stage=$(/usr/bin/mktemp -d /run/cachyfreeze-installer.XXXXXXXX)
    cleanup_stage() { /usr/bin/rm -rf --one-file-system "$stage"; }
    trap cleanup_stage ERR
    /usr/bin/cp -a -- "$source_root/." "$stage/"
    cd "$stage"
    [[ $(/usr/bin/sha256sum .cachyfreeze-payload.sha256 | /usr/bin/cut -d" " -f1) == "$expected_hash" ]]
    /usr/bin/sha256sum --strict -c .cachyfreeze-payload.sha256 >/dev/null
    [[ $(/usr/bin/find . -type f ! -name .cachyfreeze-payload.sha256 | /usr/bin/wc -l) -eq $(/usr/bin/wc -l <.cachyfreeze-payload.sha256) ]]
    ! /usr/bin/find . ! -type d ! -type f -print -quit | /usr/bin/grep -q .
    /usr/bin/chown -R root:root "$stage"
    /usr/bin/chmod -R go-w "$stage"
    /usr/bin/chmod 0755 "$stage"
    /usr/bin/touch "$stage/.cachyfreeze-root-staged"
    /usr/bin/chmod 0444 "$stage/.cachyfreeze-root-staged"
    trap - ERR
    printf "%s\n" "$stage"
  ' cachyfreeze-stage "$payload_root" "$expected_manifest_hash"
) || {
  show_error "The root-owned installer payload could not be staged."
  exit 1
}
[[ $staged_root == /run/cachyfreeze-installer.* && -d $staged_root ]] || {
  show_error "The privileged installer returned an invalid staging path."
  exit 1
}
/usr/bin/bash "$staged_root/app/cachy-freeze-setup"
exit $?
__CACHYFREEZE_PAYLOAD_BELOW__
HEADER

source_epoch=${SOURCE_DATE_EPOCH:-0}
payload_root=$work/payload
install -d "$payload_root"
tar \
  --sort=name \
  --mtime="@$source_epoch" \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  --exclude='*/__pycache__' \
  --exclude='*.py[co]' \
  -C "$PROJECT_ROOT" \
  -cf - \
  VERSION \
  src/cachy_freeze \
  app/cachy-freeze-manager \
  app/cachy-freeze-manager-helper \
  app/cachy-freeze-manager.desktop \
  app/cachy-freeze-setup \
  app/cachy_freeze_gui \
  app/org.cachyos.cachy-freeze.policy \
  installer/configure-grub-password.sh \
  installer/install-cachyfreeze.sh \
  installer/install-freeze-engine.sh \
  deepfreeze/bin \
  deepfreeze/etc \
  deepfreeze/grub \
  deepfreeze/initcpio \
  deepfreeze/systemd |
  tar -xf - -C "$payload_root"
(
  cd "$payload_root"
  find . -type f ! -name .cachyfreeze-payload.sha256 -print0 |
    sort -z |
    xargs -0 sha256sum >.cachyfreeze-payload.sha256
)
manifest_hash=$(sha256sum "$payload_root/.cachyfreeze-payload.sha256" | cut -d' ' -f1)
sed -i "s/__CACHYFREEZE_MANIFEST_HASH__/$manifest_hash/" "$work/header"
tar \
  --sort=name \
  --mtime="@$source_epoch" \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  -C "$payload_root" \
  -cf - . |
  gzip -n >"$work/payload.tar.gz"

cp "$work/header" "$output"
dd if="$work/payload.tar.gz" of="$output" oflag=append conv=notrunc status=none
chmod 0755 "$output"
(
  cd "$output_dir"
  sha256sum "${output##*/}" >"${output##*/}.sha256"
)
printf '%s\n' "$output"
