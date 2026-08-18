#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=lib/common.sh
source "$PROJECT_ROOT/installer/lib/common.sh"

require_root
require_maintenance

pacman -Syu --needed --noconfirm \
  alsa-lib \
  base-devel \
  curl \
  file \
  git \
  glib2-devel \
  gobject-introspection \
  gtk3 \
  gtk-doc \
  libcups \
  libappindicator-gtk3 \
  libnotify \
  libsecret \
  libxss \
  libxtst \
  libreoffice-fresh \
  libreoffice-fresh-tr \
  lsb-release \
  kdialog \
  kwallet \
  nss \
  python-pyqt6 \
  rsync \
  ttf-liberation \
  unzip \
  v4l-utils \
  wget \
  wine-staging \
  wine-gecko \
  wine-mono \
  winetricks \
  xdg-utils \
  xorg-server-xvfb \
  7zip

aur_install google-chrome
aur_install slack-desktop
# GTK 2 was moved from the official Arch repositories to AUR. Zoiper still
# links against it, so resolve the legacy runtime through the same unprivileged
# and verified makepkg path used for the other AUR packages.
aur_install gtk2
aur_install zoiper-bin
aur_install anydesk-bin
if systemctl list-unit-files anydesk.service >/dev/null 2>&1; then
  systemctl enable anydesk.service
fi

install -d -m 0755 /opt/company/microsip
install -d -m 0700 /var/cache/cachyos-workstation/microsip
microsip_download_page=https://www.microsip.org/downloads
microsip_page_file=/var/cache/cachyos-workstation/microsip/downloads.html
download_https "$microsip_download_page" "$microsip_page_file"
microsip_page=$(<"$microsip_page_file")
microsip_path=$(
  grep -m1 -oE '/download/MicroSIP-[0-9.]+\.zip' <<<"$microsip_page"
)
[[ -n $microsip_path ]] ||
  die "A portable ZIP link was not found on the official MicroSIP page."
microsip_url="https://www.microsip.org$microsip_path"
microsip_zip="/opt/company/microsip/${microsip_path##*/}"

if [[ ! -s $microsip_zip ]]; then
  download_https "$microsip_url" "$microsip_zip"
fi
microsip_size=$(stat -c %s "$microsip_zip")
(( microsip_size >= 1048576 && microsip_size <= 104857600 )) ||
  die "The MicroSIP portable archive has an unexpected size: $microsip_size"
unzip -t "$microsip_zip"
validate_zip_paths "$microsip_zip"
unzip -Z1 "$microsip_zip" |
  grep -Eix 'MicroSIP\.exe' >/dev/null ||
  die "microsip.exe was not found in the MicroSIP portable archive."
[[ $(unzip -Z1 "$microsip_zip" | grep -Eic '^MicroSIP\.exe$') -eq 1 ]] ||
  die "The MicroSIP portable archive must contain exactly one MicroSIP.exe."

microsip_verify_stage=$(mktemp -d /tmp/cachy-microsip-verify.XXXXXX)
trap 'rm -rf --one-file-system "$microsip_verify_stage"' EXIT
unzip -q "$microsip_zip" -d "$microsip_verify_stage"
file "$microsip_verify_stage/MicroSIP.exe" | grep -q 'PE32' ||
  die "MicroSIP.exe is not a valid Windows PE file."
microsip_exe_sha256=$(sha256sum "$microsip_verify_stage/MicroSIP.exe" | awk '{print $1}')
[[ $microsip_exe_sha256 =~ ^[0-9a-f]{64}$ ]] ||
  die "The MicroSIP.exe checksum could not be created."
rm -rf --one-file-system "$microsip_verify_stage"
trap - EXIT

printf '%s\n' "${microsip_zip##*/}" >/opt/company/microsip/CURRENT
microsip_archive_sha256=$(sha256sum "$microsip_zip" | awk '{print $1}')
printf '%s  %s\n' "$microsip_archive_sha256" "${microsip_zip##*/}" \
  >/opt/company/microsip/SHA256SUMS
python - "$microsip_url" "$microsip_archive_sha256" "$microsip_exe_sha256" \
  >/opt/company/microsip/metadata.json <<'PY'
import json
import sys
from datetime import UTC, datetime

print(json.dumps({
    "schema": 1,
    "source_url": sys.argv[1],
    "downloaded_at": datetime.now(UTC).isoformat(),
    "archive_sha256": sys.argv[2],
    "executable_sha256": sys.argv[3],
}, sort_keys=True))
PY
chmod 0644 \
  "$microsip_zip" \
  /opt/company/microsip/CURRENT \
  /opt/company/microsip/SHA256SUMS \
  /opt/company/microsip/metadata.json

install -d -m 0755 /etc/opt/chrome/policies/managed
install -m 0644 \
  "$PROJECT_ROOT/policies/chrome/managed.json" \
  /etc/opt/chrome/policies/managed/company.json

for command in google-chrome-stable slack wine libreoffice zoiper anydesk; do
  command -v "$command" >/dev/null ||
    die "A required command is missing after installation: $command"
done
unzip -t "$microsip_zip"
(cd /opt/company/microsip && sha256sum --check SHA256SUMS)

printf '%s\n' \
  "Managed applications were installed and verified." \
  "The per-user MicroSIP prefix will be created while preparing the account."
