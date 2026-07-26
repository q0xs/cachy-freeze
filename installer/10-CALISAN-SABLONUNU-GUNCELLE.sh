#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALLER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
source "$INSTALLER_DIR/lib/common.sh"

require_root
require_maintenance

readonly CONFIG=/etc/cachy-employee.conf
[[ -r $CONFIG ]] || die "Calisan yapilandirmasi bulunamadi."
# Dosya root tarafindan olusturulur ve yalnizca root yazabilir.
# shellcheck disable=SC1090
source "$CONFIG"

[[ ${EMPLOYEE_USER:-} =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
  die "Gecersiz calisan hesabi yapilandirmasi."
id "$EMPLOYEE_USER" >/dev/null 2>&1 ||
  die "Calisan hesabi bulunamadi: $EMPLOYEE_USER"

# Kopya alinirken kullanici sureclerinin dosya degistirmesini engelle.
loginctl terminate-user "$EMPLOYEE_USER" 2>/dev/null || true

employee_home=$(getent passwd "$EMPLOYEE_USER" | cut -d: -f6)
[[ -n $employee_home && -d $employee_home ]] ||
  die "Calisan ev dizini bulunamadi."

template_root=/var/lib/cachy-employee-template
template="$template_root/$EMPLOYEE_USER"
next_template="$template_root/$EMPLOYEE_USER.next"
previous_template="$template_root/$EMPLOYEE_USER.previous"

install -d -m 0700 "$template_root"
rm -rf --one-file-system "$next_template"
cp -a "$employee_home" "$next_template"

rm -rf --one-file-system "$previous_template"
[[ ! -e $template ]] || mv "$template" "$previous_template"
mv "$next_template" "$template"

printf '%s\n' \
  "Calisan ev sablonu guncellendi: $EMPLOYEE_USER" \
  "Onceki sablon kurtarma icin korunuyor: $previous_template"

