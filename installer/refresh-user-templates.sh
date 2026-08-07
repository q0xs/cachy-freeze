#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly PROJECT_ROOT=$(cd -- "$INSTALLER_DIR/.." && pwd)
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

readonly CONFIG=/etc/cachy-employee.conf
readonly ADMIN_CONFIG=/etc/cachy-frozen-admin.conf
[[ -r $CONFIG ]] || die "Calisan yapilandirmasi bulunamadi."
if [[ ! -r $ADMIN_CONFIG ]]; then
  printf '%s\n' 'ADMIN_USER=localadm' >"$ADMIN_CONFIG"
  chmod 0600 "$ADMIN_CONFIG"
fi
# Dosya root tarafindan olusturulur ve yalnizca root yazabilir.
# shellcheck disable=SC1090
source "$CONFIG"
# shellcheck disable=SC1090
source "$ADMIN_CONFIG"

[[ ${EMPLOYEE_USER:-} =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
  die "Gecersiz calisan hesabi yapilandirmasi."
[[ ${ADMIN_USER:-} =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
  die "Gecersiz yonetici hesabi yapilandirmasi."
id "$EMPLOYEE_USER" >/dev/null 2>&1 ||
  die "Calisan hesabi bulunamadi: $EMPLOYEE_USER"
id "$ADMIN_USER" >/dev/null 2>&1 ||
  die "Yonetici hesabi bulunamadi: $ADMIN_USER"

# Eski kurulumlari iki-kullanici reset duzenine tasir.
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-employee-reset" \
  /usr/local/sbin/cachy-employee-reset
install -m 0644 \
  "$PROJECT_ROOT/user/files/cachy-employee-reset.service" \
  /etc/systemd/system/cachy-employee-reset.service
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict" \
  /usr/local/sbin/cachy-frozen-admin-restrict
install -m 0644 \
  "$PROJECT_ROOT/user/files/cachy-frozen-admin-restrict.service" \
  /etc/systemd/system/cachy-frozen-admin-restrict.service

# Eski Frozen servisinin nologin degisikligi Golden'a tasinmasin.
usermod --shell /bin/bash "$ADMIN_USER"
systemctl daemon-reload
systemctl enable cachy-employee-reset.service
systemctl enable cachy-frozen-admin-restrict.service

# Kopya alinirken kullanici sureclerinin dosya degistirmesini engelle.
loginctl terminate-user "$EMPLOYEE_USER" 2>/dev/null || true

template_root=/var/lib/cachy-user-template
install -d -m 0700 "$template_root"
for user in "$EMPLOYEE_USER" "$ADMIN_USER"; do
  user_home=$(getent passwd "$user" | cut -d: -f6)
  [[ -n $user_home && -d $user_home ]] ||
    die "Ev dizini bulunamadi: $user"
  template="$template_root/$user"
  next_template="$template_root/$user.next"
  previous_template="$template_root/$user.previous"

  rm -rf --one-file-system "$next_template"
  cp -a "$user_home" "$next_template"
  rm -rf --one-file-system "$previous_template"
  [[ ! -e $template ]] || mv "$template" "$previous_template"
  mv "$next_template" "$template"

  printf '%s\n' \
    "Kullanici ev sablonu guncellendi: $user" \
    "Onceki sablon kurtarma icin korunuyor: $previous_template"
done
