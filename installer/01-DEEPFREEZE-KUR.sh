#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly DF_ROOT=$PROJECT_ROOT/deepfreeze

die() {
  printf 'HATA: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "Su sekilde calistir: sudo $0"
[[ -r $DF_ROOT/bin/cachy-freeze ]] || die "Deep Freeze proje dosyalari eksik."

CACHY_FREEZE_CONFIG="$DF_ROOT/etc/cachy-freeze.conf" \
  bash "$DF_ROOT/bin/cachy-freeze" preflight

root_uuid=$(findmnt -n -o UUID /)
[[ -n $root_uuid ]] || die "Kok Btrfs UUID bulunamadi."
[[ $(findmnt -n -o SOURCE /) == *'[/@]' ]] ||
  die "Kurulum yalnizca Maintenance @ kokunde yapilir."
root_options=$(findmnt -n -o OPTIONS /)
[[ ,$root_options, == *,rw,* ]] ||
  die "Maintenance @ koku salt-okunur bagli; Deep Freeze kurulumu yapilamaz."

backup_dir="/var/lib/cachy-freeze/install-backup/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$backup_dir"
cp -a /etc/mkinitcpio.conf /etc/default/grub /boot/grub/grub.cfg "$backup_dir/"
cp -a /etc/grub.d "$backup_dir/"

install -d -m 0755 \
  /usr/lib/cachy-freeze \
  /etc/initcpio/install \
  /etc/grub.d \
  /usr/local/sbin
install -m 0755 "$DF_ROOT/bin/cachy-freeze" /usr/local/sbin/cachy-freeze
install -m 0755 \
  "$DF_ROOT/initcpio/cachy-freeze-reset" \
  /usr/lib/cachy-freeze/cachy-freeze-reset
install -m 0644 \
  "$DF_ROOT/initcpio/cachy-freeze-reset.service" \
  /usr/lib/systemd/system/cachy-freeze-reset.service
install -m 0644 "$DF_ROOT/initcpio/install-hook" /etc/initcpio/install/cachy-freeze
install -m 0755 "$DF_ROOT/grub/40_cachy_freeze" /etc/grub.d/40_cachy_freeze
install -m 0755 "$DF_ROOT/grub/01_cachy_auth" /etc/grub.d/01_cachy_auth

sed "s/^ROOT_UUID=.*/ROOT_UUID=$root_uuid/" \
  "$DF_ROOT/etc/cachy-freeze.conf" >/etc/cachy-freeze.conf
chmod 0600 /etc/cachy-freeze.conf

cat >/etc/cachy-freeze-initrd.conf <<EOF
ROOT_UUID=$root_uuid
MAINTENANCE_SUBVOL=@
GOLDEN_SUBVOL=@golden
ACTIVE_SUBVOL=@active
PREVIOUS_SUBVOL=@active.previous
NEXT_SUBVOL=@active.next
EOF
chmod 0600 /etc/cachy-freeze-initrd.conf

if ! grep -Eq '^HOOKS=.*\bcachy-freeze\b' /etc/mkinitcpio.conf; then
  sed -i -E \
    '/^HOOKS=/s/[[:space:]]+filesystems([[:space:]]*\))/ cachy-freeze filesystems\1/' \
    /etc/mkinitcpio.conf
fi
grep -Eq '^HOOKS=.*\bsystemd\b.*\bcachy-freeze\b.*\bfilesystems\b' \
  /etc/mkinitcpio.conf ||
  die "mkinitcpio HOOKS guvenli sekilde guncellenemedi."

sed -i -E "s/^GRUB_DEFAULT=.*/GRUB_DEFAULT=saved/" /etc/default/grub
if grep -q '^GRUB_DISABLE_OS_PROBER=' /etc/default/grub; then
  sed -i -E "s/^GRUB_DISABLE_OS_PROBER=.*/GRUB_DISABLE_OS_PROBER=true/" \
    /etc/default/grub
else
  printf '%s\n' 'GRUB_DISABLE_OS_PROBER=true' >>/etc/default/grub
fi
if grep -q '^GRUB_SAVEDEFAULT=' /etc/default/grub; then
  sed -i -E "s/^GRUB_SAVEDEFAULT=.*/GRUB_SAVEDEFAULT=false/" /etc/default/grub
else
  printf '%s\n' 'GRUB_SAVEDEFAULT=false' >>/etc/default/grub
fi

# Yalnızca iki kurumsal girişi göster. Diğer üreticiler silinmez; çalıştırma
# izinleri kapatılır ve yukarıdaki kurulum yedeğinde özgün halleri korunur.
for generator in /etc/grub.d/*; do
  [[ -f $generator ]] || continue
  case ${generator##*/} in
    00_header | 01_cachy_auth | 05_debian_theme | 40_cachy_freeze)
      chmod a+x "$generator"
      ;;
    *)
      chmod a-x "$generator"
      ;;
  esac
done

mkinitcpio -P
grub-mkconfig -o /boot/grub/grub.cfg

for image in /boot/initramfs-linux-cachyos.img /boot/initramfs-linux-cachyos-lts.img; do
  [[ -r $image ]] || continue
  lsinitcpio "$image" | grep -qx 'usr/lib/cachy-freeze/cachy-freeze-reset' ||
    die "Reset programi initramfs icinde yok: $image"
done
for entry in cachyos-frozen cachyos-maintenance; do
  grep -q -- "--id '$entry'" /boot/grub/grub.cfg ||
    die "GRUB girisi eksik: $entry"
done
[[ $(grep -c '^menuentry ' /boot/grub/grub.cfg) -eq 2 ]] ||
  die "GRUB menusunde iki disinda giris bulundu."

/usr/local/sbin/cachy-freeze thaw

printf '%s\n' \
  "Deep Freeze kuruldu ve test edildi." \
  "Guvenli varsayilan: Maintenance." \
  "Golden henuz yayinlanmadi; 06-GOLDEN-YAYINLA.sh calistirilmali." \
  "Frozen moda gecmek icin 04-DONDUR.sh dosyasini ayrica calistir."
