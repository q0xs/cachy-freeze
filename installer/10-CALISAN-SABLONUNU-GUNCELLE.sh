#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

readonly CONFIG=/etc/cachy-employee.conf
readonly ADMIN_CONFIG=/etc/cachy-frozen-admin.conf
[[ -r $CONFIG ]] || die "Calisan yapilandirmasi bulunamadi."
[[ -r $ADMIN_CONFIG ]] || die "Yonetici yapilandirmasi bulunamadi."
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
