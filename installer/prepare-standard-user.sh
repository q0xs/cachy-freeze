#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly PROJECT_ROOT

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Standard-user preparation requires root privileges."
(( $# == 1 )) || die "Exactly one username is required."
readonly username=$1
[[ $username =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] || die "Invalid username."
[[ $username != localadm ]] || die "The administrator account cannot be prepared as standard."

account=$(getent passwd "$username") || die "User not found: $username"
IFS=: read -r _ _ uid gid _ home shell <<<"$account"
(( uid >= 1000 && uid < 65534 )) || die "The account is not a regular local user."
[[ $shell != */nologin && $shell != */false ]] || die "The account does not have a login shell."
[[ -d $home && $home == /home/* ]] || die "The user home is not a supported /home directory."

groups=$(id -nG "$username")
if grep -Eq '(^| )(wheel|sudo)( |$)' <<<"$groups"; then
  die "The new account unexpectedly has administrator membership."
fi

for command in wine unzip rsync google-chrome-stable slack libreoffice zoiper anydesk \
  xvfb-run runuser; do
  command -v "$command" >/dev/null ||
    die "Required application is missing: $command. Install or repair applications first."
done

readonly microsip_root=/opt/company/microsip
[[ -s $microsip_root/CURRENT ]] || die "The verified MicroSIP archive is not installed."
microsip_archive_name=$(<"$microsip_root/CURRENT")
readonly microsip_archive_name
[[ ${microsip_archive_name##*/} == "$microsip_archive_name" ]] ||
  die "The MicroSIP archive name is invalid."
readonly microsip_archive=$microsip_root/$microsip_archive_name
[[ -s $microsip_archive ]] || die "The verified MicroSIP archive is missing."
(cd "$microsip_root" && sha256sum --check SHA256SUMS >/dev/null) ||
  die "The MicroSIP archive checksum is invalid."

install -d -o "$uid" -g "$gid" -m 0755 \
  "$home/Desktop" "$home/.config" "$home/.local/share/applications" \
  "$home/.local/share/company-wine"
install -o "$uid" -g "$gid" -m 0644 \
  "$PROJECT_ROOT/user/files/kdeglobals" "$home/.config/kdeglobals"
install -o "$uid" -g "$gid" -m 0644 \
  "$PROJECT_ROOT/user/files/plasmarc" "$home/.config/plasmarc"
for desktop in "$PROJECT_ROOT"/user/desktop/*.desktop; do
  install -o "$uid" -g "$gid" -m 0555 "$desktop" "$home/Desktop/${desktop##*/}"
done

cat >"$home/.config/mimeapps.list" <<'EOF'
[Default Applications]
x-scheme-handler/http=google-chrome.desktop
x-scheme-handler/https=google-chrome.desktop
text/html=google-chrome.desktop

[Added Associations]
x-scheme-handler/http=google-chrome.desktop;
x-scheme-handler/https=google-chrome.desktop;
text/html=google-chrome.desktop;
EOF
chown "$uid:$gid" "$home/.config/mimeapps.list"
chmod 0644 "$home/.config/mimeapps.list"

readonly prefix=$home/.local/share/company-wine/microsip
install -d -o "$uid" -g "$gid" -m 0700 "$prefix"
set +e
timeout --signal=TERM --kill-after=10s 120s \
  runuser -u "$username" -- \
  env WINEPREFIX="$prefix" WINEARCH=win64 WINEDEBUG=-all xvfb-run -a wineboot -u
wineboot_rc=$?
set -e
runuser -u "$username" -- env WINEPREFIX="$prefix" wineserver -k >/dev/null 2>&1 || true
(( wineboot_rc == 0 || wineboot_rc == 124 )) ||
  die "MicroSIP Wine initialization failed (code: $wineboot_rc)."
[[ -s $prefix/system.reg ]] || die "The MicroSIP Wine prefix was not created."

stage=$(mktemp -d /tmp/cachy-microsip-user.XXXXXX)
readonly stage
cleanup() { rm -rf --one-file-system "$stage"; }
trap cleanup EXIT
unzip -q "$microsip_archive" -d "$stage"
microsip_exe=$(find "$stage" -type f -iname microsip.exe -print -quit)
[[ -n $microsip_exe ]] || die "MicroSIP.exe was not found in the verified archive."
readonly target=$prefix/drive_c/Program\ Files/MicroSIP
install -d -o "$uid" -g "$gid" -m 0755 "$target"
rsync -a --delete "${microsip_exe%/*}/" "$target/"
installed_exe=$(find "$target" -maxdepth 1 -type f -iname microsip.exe -print -quit)
[[ -n $installed_exe ]] || die "MicroSIP.exe was not installed into the user prefix."
if [[ $installed_exe != "$target/microsip.exe" ]]; then
  mv "$installed_exe" "$target/microsip.exe"
fi
chown -R "$uid:$gid" "$home"
chmod 0755 "$target/microsip.exe"

printf 'Standard user prepared with verified applications: %s\n' "$username"
