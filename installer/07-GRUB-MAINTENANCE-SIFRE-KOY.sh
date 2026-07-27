#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly AUTH_GENERATOR=$PROJECT_ROOT/deepfreeze/grub/01_cachy_auth
readonly AUTH_CONFIG=/etc/cachy-freeze-grub-auth.conf
readonly AUTH_USER=cachyadmin

die() {
  printf 'HATA: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Su sekilde calistir: sudo $0"
command -v grub-mkpasswd-pbkdf2 >/dev/null ||
  die "grub-mkpasswd-pbkdf2 bulunamadi."
command -v grub-mkconfig >/dev/null || die "grub-mkconfig bulunamadi."
[[ -r $AUTH_GENERATOR ]] || die "GRUB yetkilendirme dosyasi eksik."

printf '%s\n' \
  "GRUB Maintenance kullanicisi: $AUTH_USER" \
  "Simdi iki kez girilecek parola ekranda gorunmez."

hash=$(
  grub-mkpasswd-pbkdf2 |
    sed -n 's/.*\(grub\.pbkdf2\.[^[:space:]]*\).*/\1/p'
)
[[ $hash == grub.pbkdf2.* ]] || die "Parola ozeti olusturulamadi."

install -m 0755 "$AUTH_GENERATOR" /etc/grub.d/01_cachy_auth
umask 077
printf 'GRUB_AUTH_USER=%q\nGRUB_AUTH_HASH=%q\n' \
  "$AUTH_USER" "$hash" >"$AUTH_CONFIG"

grub-mkconfig -o /boot/grub/grub.cfg
grep -q "^set superusers=\"$AUTH_USER\"$" /boot/grub/grub.cfg ||
  die "GRUB kullanicisi yapilandirmaya eklenemedi."
grep -q "^password_pbkdf2 $AUTH_USER " /boot/grub/grub.cfg ||
  die "GRUB parola ozeti yapilandirmaya eklenemedi."
grep -q "menuentry .*--id 'cachyos-current'.*--unrestricted" \
  /boot/grub/grub.cfg ||
  die "Tek GRUB girisi bulunamadi."
grep -q '^[[:space:]]*authenticate$' /boot/grub/grub.cfg ||
  die "THAWED parola denetimi GRUB yapilandirmasina eklenemedi."
[[ $(grep -c '^menuentry ' /boot/grub/grub.cfg) -eq 1 ]] ||
  die "GRUB menusunde birden fazla giris bulundu."

printf '%s\n' \
  "GRUB Maintenance korumasi etkinlestirildi." \
  "Kullanici adi: $AUTH_USER" \
  "Menu moda gore FROZEN veya THAWED olarak tek giris gosterir." \
  "FROZEN parolasiz; THAWED girisi GRUB parolasiyla korunur."
