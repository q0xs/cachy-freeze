#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT
version=$(<"$PROJECT_ROOT/workstation/VERSION")
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9]+)?$ ]] || {
  printf '%s\n' "ERROR: Invalid workstation/VERSION." >&2
  exit 1
}

output_dir=$PROJECT_ROOT/dist
output=$output_dir/CachyWorkstation-Setup-$version.run
work=$(mktemp -d)
cleanup() {
  rm -rf --one-file-system "$work"
}
trap cleanup EXIT
install -d "$output_dir"

payload_root=$work/payload
install -d "$payload_root"
source_epoch=${SOURCE_DATE_EPOCH:-0}
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
  LICENSE \
  NOTICE \
  workstation/VERSION \
  workstation/assets \
  workstation/bin \
  workstation/idle \
  workstation/lib \
  workstation/systemd \
  workstation/vendor |
  tar -xf - -C "$payload_root"

(
  cd "$payload_root"
  find . -type f -print0 |
    LC_ALL=C sort -z |
    xargs -0 sha256sum
) >"$work/payload-files.sha256"
(
  cd "$payload_root"
  find . -type l -printf '%P\t%l\n' | LC_ALL=C sort
) >"$work/payload-symlinks"
install -m 0644 "$work/payload-files.sha256" "$payload_root/.cws-payload-files.sha256"
install -m 0644 "$work/payload-symlinks" "$payload_root/.cws-payload-symlinks"
file_manifest_hash=$(sha256sum "$payload_root/.cws-payload-files.sha256" | cut -d' ' -f1)
symlink_manifest_hash=$(sha256sum "$payload_root/.cws-payload-symlinks" | cut -d' ' -f1)

cat >"$work/header" <<'HEADER'
#!/usr/bin/env bash
set -Eeuo pipefail

show_error() {
  printf 'ERROR: %s\n' "$1" >&2
}

(( EUID == 0 )) || {
  show_error "Run this portable installer with sudo: sudo ./${0##*/} USER"
  exit 1
}
[[ $(uname -m) == x86_64 ]] || {
  show_error "Only x86_64 CachyOS/Arch workstations are supported."
  exit 1
}

umask 077
exec 9<"$0"
payload_root=$(mktemp -d /run/cachy-workstation-setup.XXXXXXXX) || exit 1
link_inventory=$(mktemp /run/cachy-workstation-links.XXXXXXXX) || exit 1
cleanup() {
  rm -f -- "$link_inventory"
  rm -rf --one-file-system "$payload_root"
}
trap cleanup EXIT INT TERM

payload_line=__CWS_PAYLOAD_LINE__
if ! tail -n +"$payload_line" <&9 | gzip -dc | tar --no-same-owner -xf - -C "$payload_root"; then
  show_error "The embedded workstation payload is corrupt."
  exit 1
fi
exec 9<&-

expected_file_manifest_hash=__CWS_FILE_MANIFEST_HASH__
expected_symlink_manifest_hash=__CWS_SYMLINK_MANIFEST_HASH__
file_manifest=$payload_root/.cws-payload-files.sha256
symlink_manifest=$payload_root/.cws-payload-symlinks
[[ -f $file_manifest && -f $symlink_manifest ]] || {
  show_error "The embedded integrity manifests are missing."
  exit 1
}
[[ $(sha256sum "$file_manifest" | cut -d' ' -f1) == "$expected_file_manifest_hash" ]] || {
  show_error "The embedded file manifest was modified."
  exit 1
}
[[ $(sha256sum "$symlink_manifest" | cut -d' ' -f1) == "$expected_symlink_manifest_hash" ]] || {
  show_error "The embedded symlink manifest was modified."
  exit 1
}
(
  cd "$payload_root"
  sha256sum --strict --check .cws-payload-files.sha256 >/dev/null
) || {
  show_error "An embedded workstation file failed its checksum."
  exit 1
}
expected_file_count=$(wc -l <"$file_manifest")
actual_file_count=$(
  find "$payload_root" -type f \
    ! -name .cws-payload-files.sha256 \
    ! -name .cws-payload-symlinks |
    wc -l
)
[[ $actual_file_count -eq $expected_file_count ]] || {
  show_error "The embedded payload contains an unlisted file."
  exit 1
}
find "$payload_root" -type l -printf '%P\t%l\n' | LC_ALL=C sort >"$link_inventory"
cmp -s "$link_inventory" "$symlink_manifest" || {
  show_error "The embedded symlink inventory is invalid."
  exit 1
}
! find "$payload_root" ! -type d ! -type f ! -type l -print -quit | grep -q . || {
  show_error "The embedded payload contains an unsupported file type."
  exit 1
}

chown -R root:root "$payload_root"
chmod -R go-w "$payload_root"
chmod 0755 "$payload_root"

set +e
/usr/bin/bash "$payload_root/workstation/bin/workstation-setup" "$@"
status=$?
set -e
exit "$status"
__CACHY_WORKSTATION_PAYLOAD_BELOW__
HEADER

header_lines=$(wc -l <"$work/header")
payload_line=$(( header_lines + 1 ))
sed -i \
  -e "s/__CWS_PAYLOAD_LINE__/$payload_line/" \
  -e "s/__CWS_FILE_MANIFEST_HASH__/$file_manifest_hash/" \
  -e "s/__CWS_SYMLINK_MANIFEST_HASH__/$symlink_manifest_hash/" \
  "$work/header"

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
