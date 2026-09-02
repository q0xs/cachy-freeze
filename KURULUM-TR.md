# CachyFreeze Kurulum Rehberi

Bu rehber tek dosyalik grafik installer ile hem Workstation hazirligini hem de
CachyFreeze kurulumunu yapar. Hedef bilgisayarda GitHub hesabi veya `git clone`
gerekmez.

## Kisa Ozet

Dogru sira sudur:

1. CachyOS kur.
2. Calisan kullaniciyi standart kullanici olarak olustur.
3. `CachyFreeze-Installer-1.0.0rc7.run` dosyasini indir.
4. Installer icinden **INSTALL / REPAIR WORKSTATION** calistir.
5. Calisan hesabinda uygulamalari elle test et.
6. Installer icinden **CHECK WORKSTATION** calistir.
7. Her sey PASS ise **INSTALL CACHYFREEZE** calistir.
8. Yeniden baslat ve FROZEN durumunu kontrol et.

Workstation kurulumu veya onarimi FROZEN durumda yapilmaz. Gerekirse once
**THAW COMPUTER** yapip yeniden baslatin.

## Gereken Sistem

- CachyOS veya Arch Linux
- KDE Plasma
- UEFI + GRUB
- Btrfs root subvolume `@`
- EFI bolumu `/boot/efi` olarak bagli
- `/boot` ayri bolum degil, Btrfs root icinde
- internet baglantisi
- kurtarma USB'si ve geri yuklenebilir yedek

## 1. Sistemi Hazirla

Yonetici hesabinda Konsole acin:

```bash
sudo pacman -Syu --needed curl
sudo systemctl reboot
```

Bilgisayar acilinca yonetici hesabina tekrar girin.

## 2. Calisan Hesabini Olustur

KDE **Sistem Ayarlari > Kullanicilar** bolumunden calisan hesabini olusturun.

Kurallar:

- hesap tipi standart kullanici olsun;
- `sudo`, `wheel`, `docker`, `lxd` veya yonetici yetkisi vermeyin;
- calisan hesabina bir kez giris yapin;
- KDE masaustu acilinca cikis yapip yonetici hesabina geri donun.

Ornek kullanici adi: `wrw1166`

## 3. Installer'i Indir

Yonetici hesabinda Konsole acin:

```bash
mkdir -p "$HOME/CachyKurulum"
cd "$HOME/CachyKurulum"

curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc7/CachyFreeze-Installer-1.0.0rc7.run"
curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc7/CachyFreeze-Installer-1.0.0rc7.run.sha256"
```

## 4. Dosyayi Dogrula

```bash
cd "$HOME/CachyKurulum"
sha256sum --check CachyFreeze-Installer-1.0.0rc7.run.sha256
```

Sonuc su olmali:

```text
CachyFreeze-Installer-1.0.0rc7.run: OK
```

`FAILED` gorurseniz kurulum yapmayin. Dosyalari silip tekrar indirin.

Calistirma izni verin:

```bash
chmod 0755 CachyFreeze-Installer-1.0.0rc7.run
```

## 5. Workstation'i Kur

Installer'i `sudo` ile baslatmayin:

```bash
cd "$HOME/CachyKurulum"
./CachyFreeze-Installer-1.0.0rc7.run
```

Acik pencerede:

1. PolicyKit yonetici onayini verin.
2. **Employee username** alanina calisan kullanici adini yazin.
3. **INSTALL / REPAIR WORKSTATION** dugmesine basin.
4. Islem bitene kadar pencereyi kapatmayin.

Bu adim Google Chrome, LibreOffice, AnyDesk, Zoiper, MicroSIP/Wine,
masaustu kisayollari ve 60/120 dakika bosta kalma politikasini kurar.

Basarili sonuc:

```text
OVERALL: PASS
READY FOR FREEZE
```

FAIL gorurseniz **INSTALL / REPAIR WORKSTATION** dugmesine tekrar basin.

## 6. Uygulamalari Elle Test Et

Calisan hesabina girin ve su uygulamalari tek tek acin:

1. Google Chrome
2. LibreOffice
3. AnyDesk
4. Zoiper
5. MicroSIP

Kisayollar hem masaustunde hem de uygulama menusunde gorunmelidir.

## 7. Son Kontrolu Yap

Yonetici hesabina donun. Installer penceresi kapaliysa tekrar acin:

```bash
cd "$HOME/CachyKurulum"
./CachyFreeze-Installer-1.0.0rc7.run
```

Sonra:

1. **Employee username** alanina calisan kullanici adini yazin.
2. **CHECK WORKSTATION** dugmesine basin.

Devam etmek icin sonuc mutlaka su olmali:

```text
OVERALL: PASS
Ready for freeze: YES
```

FAIL varsa henuz dondurmayin. Once Workstation repair yapin, uygulamalari
tekrar test edin, sonra check'i yeniden calistirin.

## 8. CachyFreeze'i Kur

Ayni installer penceresinde:

1. GRUB bakim parolasini iki kez girin.
2. **INSTALL CACHYFREEZE** dugmesine basin.
3. Basari mesaji gelene kadar bekleyin.
4. **REBOOT NOW** dugmesine basin.

Kurulum otomatik yeniden baslatma yapmaz. Reboot dugmesine siz basarsiniz.

## 9. FROZEN Testi

Yeniden basladiktan sonra:

1. CachyFreeze uygulamasini acin.
2. Durumun **FROZEN** oldugunu kontrol edin.
3. Calisan hesabinda gecici bir dosya olusturun.
4. Bilgisayari yeniden baslatin.
5. Gecici dosyanin silindigini kontrol edin.

## Mevcut CachyFreeze Kuruluysa

1. CachyFreeze'i acin.
2. **THAW COMPUTER** dugmesine basin.
3. **REBOOT NOW** ile yeniden baslatin.
4. Uygulama **THAWED** gosterince Workstation kurulum/repair yapin.
5. **CHECK WORKSTATION** PASS olsun.
6. Calisan uygulamalarini elle test edin.
7. **FREEZE COMPUTER** yapin.
8. **REBOOT NOW** ile FROZEN moda donun.
