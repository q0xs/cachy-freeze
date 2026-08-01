#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly ADMIN_USER=localadm
# shellcheck source=lib/common.sh
source "$PROJECT_ROOT/installer/lib/common.sh"

require_root
require_maintenance

id "$ADMIN_USER" >/dev/null 2>&1 ||
  die "Beklenen yonetici hesabi bulunamadi: $ADMIN_USER"
id -nG "$ADMIN_USER" | grep -Eq '(^| )wheel( |$)' ||
  die "$ADMIN_USER wheel grubunda degil; yonetici hesabi dogrulanamadi."
[[ $(passwd -S "$ADMIN_USER" | awk '{print $2}') == P ]] ||
  die "$ADMIN_USER icin etkin bir parola ayarlanmamis."
if getent group nopasswdlogin >/dev/null; then
  gpasswd -d "$ADMIN_USER" nopasswdlogin 2>/dev/null || true
fi

[[ -r /dev/tty && -w /dev/tty ]] ||
  die "Kullanici bilgilerini girmek icin etkilesimli terminal gerekli."

printf '%s\n' \
  "Calisan hesabi bilgileri" \
  "Kullanici adi kucuk harf, rakam, _ ve - icerebilir." >/dev/tty

read -r -p "Kullanici adi (ornek: ahmet): " employee_user </dev/tty
employee_user=${employee_user,,}
[[ $employee_user =~ ^[a-z][a-z0-9_-]{2,31}$ ]] ||
  die "Gecersiz kullanici adi: $employee_user"
[[ $employee_user != "$ADMIN_USER" ]] ||
  die "Calisan ve yonetici adi ayni olamaz."
if id "$employee_user" >/dev/null 2>&1; then
  configured_employee=$(
    sed -n 's/^EMPLOYEE_USER=//p' /etc/cachy-employee.conf 2>/dev/null || true
  )
  [[ $configured_employee == "$employee_user" ]] ||
    die "Bu kullanici zaten var ve yonetilen calisan hesabi degil: $employee_user"
fi

read -r -p "Gorunen ad ve soyad: " employee_full_name </dev/tty
[[ -n ${employee_full_name//[[:space:]]/} ]] ||
  die "Gorunen ad bos olamaz."
[[ $employee_full_name != *:* && $employee_full_name != *$'\n'* ]] ||
  die "Gorunen ad ':' karakteri iceremez."

while :; do
  read -r -s -p "Calisan parolasi: " employee_password </dev/tty
  printf '\n' >/dev/tty
  read -r -s -p "Parolayi tekrar gir: " employee_password_again </dev/tty
  printf '\n' >/dev/tty
  [[ -n $employee_password ]] || {
    printf 'Parola bos olamaz.\n' >/dev/tty
    continue
  }
  [[ $employee_password != *:* ]] || {
    printf "Parola ':' karakteri iceremez.\n" >/dev/tty
    continue
  }
  [[ $employee_password == "$employee_password_again" ]] || {
    printf 'Parolalar ayni degil; tekrar dene.\n' >/dev/tty
    continue
  }
  break
done

for command in wine unzip rsync google-chrome-stable slack libreoffice zoiper \
  anydesk; do
  command -v "$command" >/dev/null ||
    die "Once 02-UYGULAMALARI-KUR.sh calistirilmali. Eksik: $command"
done

if ! id "$employee_user" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash \
    --comment "$employee_full_name" "$employee_user"
else
  usermod --comment "$employee_full_name" "$employee_user"
fi
printf '%s:%s\n' "$employee_user" "$employee_password" | chpasswd
unset employee_password employee_password_again

gpasswd -d "$employee_user" wheel 2>/dev/null || true
gpasswd -d "$employee_user" sudo 2>/dev/null || true
employee_groups=()
for group in audio video input realtime; do
  getent group "$group" >/dev/null && employee_groups+=("$group")
done
((${#employee_groups[@]} > 0)) &&
  usermod --append --groups \
    "$(IFS=,; printf '%s' "${employee_groups[*]}")" "$employee_user"

home=$(getent passwd "$employee_user" | cut -d: -f6)
install -d -o "$employee_user" -g "$employee_user" -m 0755 \
  "$home/Desktop" "$home/.config" "$home/.local" "$home/.local/share"
install -d -o "$employee_user" -g "$employee_user" -m 0755 \
  "$home/.local/share/applications" "$home/.local/share/company-wine"
install -o "$employee_user" -g "$employee_user" -m 0644 \
  "$PROJECT_ROOT/user/files/kdeglobals" "$home/.config/kdeglobals"
install -o "$employee_user" -g "$employee_user" -m 0644 \
  "$PROJECT_ROOT/user/files/plasmarc" "$home/.config/plasmarc"

for desktop in "$PROJECT_ROOT"/user/desktop/*.desktop; do
  install -o "$employee_user" -g "$employee_user" -m 0555 \
    "$desktop" "$home/Desktop/${desktop##*/}"
done

prefix="$home/.local/share/company-wine/microsip"
install -d -o "$employee_user" -g "$employee_user" -m 0700 "$prefix"
set +e
timeout --signal=TERM --kill-after=10s 120s \
  runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" WINEARCH=win64 WINEDEBUG=-all xvfb-run -a wineboot -u
wineboot_rc=$?
set -e
runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" wineserver -k >/dev/null 2>&1 || true
if (( wineboot_rc != 0 && wineboot_rc != 124 )); then
  die "MicroSIP Wine prefix olusturma testi basarisiz (kod: $wineboot_rc)."
fi
[[ -s $prefix/system.reg ]] || die "MicroSIP Wine prefix olusturulamadi."
microsip_target="$prefix/drive_c/Program Files/MicroSIP"
microsip_stage=$(mktemp -d)
trap 'rm -rf --one-file-system "$microsip_stage"' EXIT
unzip -q "/opt/company/microsip/$(</opt/company/microsip/CURRENT)" \
  -d "$microsip_stage"
microsip_exe=$(
  find "$microsip_stage" -type f -iname 'microsip.exe' -print -quit
)
[[ -n $microsip_exe ]] ||
  die "MicroSIP arsivinden calistirilabilir dosya cikmadi."
install -d -o "$employee_user" -g "$employee_user" -m 0755 \
  "$microsip_target"
rsync -a --delete "${microsip_exe%/*}/" "$microsip_target/"
microsip_installed_exe=$(
  find "$microsip_target" -maxdepth 1 -type f -iname 'microsip.exe' \
    -print -quit
)
[[ -n $microsip_installed_exe ]] ||
  die "MicroSIP hedef dizine kurulamadi."
if [[ $microsip_installed_exe != "$microsip_target/microsip.exe" ]]; then
  mv "$microsip_installed_exe" "$microsip_target/microsip.exe"
fi
chown -R "$employee_user:$employee_user" "$microsip_target"
chmod 0755 "$microsip_target/microsip.exe"
rm -rf --one-file-system "$microsip_stage"
trap - EXIT

# File existence alone is not a successful application install. Launch the
# portable binary in an isolated display and accept either a clean exit or a
# process that remains healthy until the smoke-test timeout.
microsip_smoke_log=$(mktemp /tmp/cachy-microsip-smoke.XXXXXX.log)
set +e
timeout --signal=TERM --kill-after=5s 15s \
  runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" WINEARCH=win64 WINEDEBUG=-all \
  xvfb-run -a wine "$microsip_target/microsip.exe" /minimized \
  >"$microsip_smoke_log" 2>&1
microsip_smoke_rc=$?
set -e
runuser -u "$employee_user" -- \
  env WINEPREFIX="$prefix" wineserver -k >/dev/null 2>&1 || true
if (( microsip_smoke_rc != 0 && microsip_smoke_rc != 124 )); then
  sed -n '1,120p' "$microsip_smoke_log" >&2
  rm -f -- "$microsip_smoke_log"
  die "MicroSIP Wine smoke testi basarisiz (kod: $microsip_smoke_rc)."
fi
rm -f -- "$microsip_smoke_log"
[[ -s $prefix/system.reg ]] || die "MicroSIP Wine prefix dogrulanamadi."

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
chown "$employee_user:$employee_user" "$home/.config/mimeapps.list"
chmod 0644 "$home/.config/mimeapps.list"

install -m 0755 \
  "$PROJECT_ROOT/user/files/company-microsip" \
  /usr/local/bin/company-microsip
install -m 0755 \
  "$PROJECT_ROOT/user/files/cachy-kurulum-oturum-kapat" \
  /usr/local/bin/cachy-kurulum-oturum-kapat
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

# Calisan wheel/sudo grubunda kalmaz. Masaustundeki ayricalikli islemler
# "yetkisiz" diye kapanmak yerine yerel yonetici parolasini ister.
install -d -m 0755 /etc/polkit-1/rules.d
sed "s/__EMPLOYEE_USER__/$employee_user/g" \
  "$PROJECT_ROOT/user/files/49-company-employee-auth.rules" \
  >/etc/polkit-1/rules.d/49-company-employee-auth.rules
chown root:root /etc/polkit-1/rules.d/49-company-employee-auth.rules
chmod 0644 /etc/polkit-1/rules.d/49-company-employee-auth.rules

cat >/etc/cachy-employee.conf <<EOF
EMPLOYEE_USER=$employee_user
EOF
chmod 0600 /etc/cachy-employee.conf

cat >/etc/cachy-frozen-admin.conf <<EOF
ADMIN_USER=$ADMIN_USER
EOF
chmod 0600 /etc/cachy-frozen-admin.conf

template_root=/var/lib/cachy-user-template
rm -rf --one-file-system "$template_root/$employee_user" \
  "$template_root/$ADMIN_USER"
install -d -m 0700 "$template_root"
cp -a "$home" "$template_root/$employee_user"
admin_home=$(getent passwd "$ADMIN_USER" | cut -d: -f6)
[[ -n $admin_home && -d $admin_home ]] ||
  die "Yonetici ev dizini bulunamadi."
cp -a "$admin_home" "$template_root/$ADMIN_USER"
systemctl daemon-reload
systemctl enable cachy-employee-reset.service
systemctl enable cachy-frozen-admin-restrict.service
systemctl is-enabled --quiet cachy-employee-reset.service ||
  die "Calisan sifirlama servisi etkinlestirilemedi."
systemctl is-enabled --quiet cachy-frozen-admin-restrict.service ||
  die "Frozen yonetici kisitlama servisi etkinlestirilemedi."

if id -nG "$employee_user" | grep -Eq '(^| )(wheel|sudo)( |$)'; then
  die "Calisan ayricalikli gruptan cikarilamadi."
fi

printf '%s\n' \
  "Calisan hesabi hazir: $employee_user ($employee_full_name)" \
  "$ADMIN_USER Frozen grafik giris ekraninda gizlenecek." \
  "Frozen modda tum yonetilen hesaplar temiz sablonlarina doner." \
  "Ayricalikli masaustu islemleri $ADMIN_USER parolasini sorar." \
  "Parola kurulum sirasinda sizin girdiginiz parola olarak ayarlandi."
