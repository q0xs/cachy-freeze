# Pilot Device Checklist

Bu paket boot zincirini, initramfs'i ve Btrfs alt birimlerini değiştirir. İlk
kurulum mutlaka yedeği alınmış bir pilot laptopta ve cihazın başında yapılmalı.

Normal kullanıcı bu belge nedeniyle terminal açmaz. Aşağıdaki komut yalnız
Codex/teknisyen tarafından salt-okunur teşhis için, grafik uygulamanın ön
kontrolünden önce ek kanıt gerektiğinde çalıştırılabilir:

```bash
sudo ./deepfreeze/bin/cachy-freeze preflight
```

Komut diski değiştirmez. Aşağıdakileri doğrular:

- UEFI ile açılmış olması
- Kök dosya sisteminin Btrfs olması
- GRUB ve mkinitcpio araçlarının bulunması
- Beklenen `@` kök alt biriminin bulunması
- `/boot` dizininin Btrfs `@` kökü içinde olması
- EFI bölümünün `/boot/efi` konumunda bağlı olması

Bu teknik ön kontrol grafik uygulamadaki **Sistem ön kontrolünü çalıştır**
adımının yerine geçmez ve başarısız sonucu atlatmak için kullanılamaz.

## Fiziksel pilot güvenlik kapısı

Sistem değişmeden önce aşağıdakilerin tamamını açıkça kaydet:

- hedef gerçekten yedekli fiziksel CachyOS pilot laptop;
- UEFI + Btrfs kök + `@` + GRUB + `/boot/efi`, ayrı `/boot` yok;
- `localadm` hesabı etkin parolalı ve `wheel` üyesi;
- internet, AC güç ve yeterli boş alan mevcut;
- önyüklenebilir CachyOS kurtarma USB'si takılabilir durumda;
- önemli kullanıcı verisinin harici ve geri yüklenebilir yedeği mevcut;
- boot değişikliği öncesi geri dönüş planı yazılı.

Bu maddelerden biri eksikse provisioning/finalize başlatılmaz. VM veya eski
snapshot sonucu fiziksel kapı yerine kullanılamaz.

## Pilot öncesi kayıt

Şu komutların çıktıları saklanmalıdır:

```bash
lsblk -f
findmnt /
findmnt /boot/efi
cat /etc/fstab
cat /etc/mkinitcpio.conf
uname -a
cat /proc/cmdline
id localadm
btrfs filesystem usage /
btrfs device stats /
```

Gerçek kurulumdan önce harici diske sistem yedeği alınmalıdır. Ana ve son
kullanıcı kurulumu için `docs/installation.md` izlenmelidir.

## Finalize öncesi fiziksel kabul

- Chrome, Slack, AnyDesk, LibreOffice, Zoiper ve Wine/MicroSIP gerçek
  pencereleri hem gereken yönetici hem çalışan oturumunda açılmalıdır.
- Gerçek mikrofon, hoparlör ve kulaklık ayrı ayrı seçilip ses giriş/çıkışı
  doğrulanmalıdır; mümkünse gerçek test araması yapılmalıdır.
- Çalışan `wheel`/`sudo` dışında kalmalı; genel ayrıcalıklı işlem `localadm`
  istemelidir. Plasma'nın güvenli giriş sorguları ise gereksiz parola penceresi
  göstermemelidir.
- Tüm testler geçmeden canlı kabul kutuları işaretlenmez ve FROZEN finalize
  başlatılmaz.

Beklenmeyen güç kesintisi veya boot bozma testi; sağlıklı Golden, harici yedek,
kurtarma USB'si, AC güç, geri dönüş snapshotı ve ayrıca açık kullanıcı onayı
olmadan yapılmaz. Golden yayını, pacman, mkinitcpio veya GRUB yazımı sırasında
güç kesilmez. `btrfs check --repair` çalıştırılmaz.
