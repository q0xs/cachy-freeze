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
microsip_download_page=https://www.microsip.org/downloads
microsip_page=$(curl --fail --location --proto '=https' --tlsv1.2 \
  "$microsip_download_page")
microsip_path=$(
  grep -m1 -oE '/download/MicroSIP-[0-9.]+\.zip' <<<"$microsip_page"
)
[[ -n $microsip_path ]] ||
  die "MicroSIP resmi sayfasinda portable ZIP baglantisi bulunamadi."
microsip_url="https://www.microsip.org$microsip_path"
microsip_zip="/opt/company/microsip/${microsip_path##*/}"

if [[ ! -s $microsip_zip ]]; then
  curl --fail --location --proto '=https' --tlsv1.2 \
    --output "$microsip_zip.download" \
    "$microsip_url"
  unzip -t "$microsip_zip.download"
  mv "$microsip_zip.download" "$microsip_zip"
fi
unzip -Z1 "$microsip_zip" |
  grep -Ei '(^|/)microsip\.exe$' >/dev/null ||
  die "MicroSIP portable arsivinde microsip.exe bulunamadi."
printf '%s\n' "${microsip_zip##*/}" >/opt/company/microsip/CURRENT
sha256sum "$microsip_zip" >/opt/company/microsip/SHA256SUMS
chmod 0644 \
  "$microsip_zip" \
  /opt/company/microsip/CURRENT \
  /opt/company/microsip/SHA256SUMS

install -d -m 0755 /etc/opt/chrome/policies/managed
install -m 0644 \
  "$PROJECT_ROOT/policies/chrome/managed.json" \
  /etc/opt/chrome/policies/managed/company.json

for command in google-chrome-stable slack wine libreoffice zoiper anydesk; do
  command -v "$command" >/dev/null ||
    die "Kurulum sonrasi komut bulunamadi: $command"
done
unzip -t "$microsip_zip"

printf '%s\n' \
  "Kurumsal uygulamalar kuruldu ve dogrulandi." \
  "MicroSIP kullanici prefix'i 03-CALISAN-KULLANICI-OLUSTUR.sh ile olusacak."
