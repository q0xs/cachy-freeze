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
  gtk2 \
  gtk3 \
  libcups \
  libappindicator-gtk3 \
  libnotify \
  libsecret \
  libxss \
  libxtst \
  libreoffice-fresh \
  libreoffice-fresh-tr \
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
  die "MicroSIP resmi sayfasinda portable ZIP baglantisi bulunamadi."
microsip_url="https://www.microsip.org$microsip_path"
microsip_zip="/opt/company/microsip/${microsip_path##*/}"

if [[ ! -s $microsip_zip ]]; then
  download_https "$microsip_url" "$microsip_zip"
fi
microsip_size=$(stat -c %s "$microsip_zip")
(( microsip_size >= 1048576 && microsip_size <= 104857600 )) ||
  die "MicroSIP portable arsiv boyutu beklenmiyor: $microsip_size"
unzip -t "$microsip_zip"
validate_zip_paths "$microsip_zip"
unzip -Z1 "$microsip_zip" |
  grep -Eix 'MicroSIP\.exe' >/dev/null ||
  die "MicroSIP portable arsivinde microsip.exe bulunamadi."
[[ $(unzip -Z1 "$microsip_zip" | grep -Eic '^MicroSIP\.exe$') -eq 1 ]] ||
  die "MicroSIP portable arsivinde tek bir MicroSIP.exe olmali."

microsip_verify_stage=$(mktemp -d /tmp/cachy-microsip-verify.XXXXXX)
trap 'rm -rf --one-file-system "$microsip_verify_stage"' EXIT
unzip -q "$microsip_zip" -d "$microsip_verify_stage"
file "$microsip_verify_stage/MicroSIP.exe" | grep -q 'PE32' ||
  die "MicroSIP.exe gecerli bir Windows PE dosyasi degil."
microsip_exe_sha256=$(sha256sum "$microsip_verify_stage/MicroSIP.exe" | awk '{print $1}')
[[ $microsip_exe_sha256 =~ ^[0-9a-f]{64}$ ]] ||
  die "MicroSIP.exe checksum olusturulamadi."
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
    die "Kurulum sonrasi komut bulunamadi: $command"
done
unzip -t "$microsip_zip"
(cd /opt/company/microsip && sha256sum --check SHA256SUMS)

printf '%s\n' \
  "Kurumsal uygulamalar kuruldu ve dogrulandi." \
  "MicroSIP kullanici prefix'i 03-CALISAN-KULLANICI-OLUSTUR.sh ile olusacak."
