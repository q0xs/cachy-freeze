# CachyFreeze Kurulum Rehberi

Bu rehber tek dosyalik grafik installer ile hem Workstation hazirligini hem de
CachyFreeze kurulumunu yapar. Hedef bilgisayarda GitHub hesabi veya `git clone`
gerekmez.

## Kisa Ozet

Dogru sira sudur:

1. CachyOS kur.
2. Calisan kullaniciyi standart kullanici olarak olustur.
3. `CachyFreeze-Installer-1.0.0rc10.run` dosyasini indir.
4. Installer icinden **INSTALL / REPAIR** calistir.
5. Calisan hesabinda uygulamalari elle test et.
6. Installer icinden **CHECK** calistir.
7. Her sey PASS ise **INSTALL CACHYFREEZE** calistir. PASS olmadan bu adim
   uygulama icinde kapali kalir.
8. Yeniden baslat ve status bolumunde **FROZEN** durumunu kontrol et.

Workstation kurulumu veya onarimi FROZEN durumda yapilmaz. Gerekirse once
**THAW COMPUTER** yapip yeniden baslatin.

CachyFreeze uygulamasinin status bolumu mevcut modu **FROZEN** veya **THAWED**
olarak gosterir. Bilinen mod hemen gorunur; yetkili dogrulama bitene kadar
islem dugmeleri guvenli sekilde kapali kalir.

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
  "https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc10/CachyFreeze-Installer-1.0.0rc10.run"
curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc10/CachyFreeze-Installer-1.0.0rc10.run.sha256"
```

## 4. Dosyayi Dogrula

```bash
cd "$HOME/CachyKurulum"
sha256sum --check CachyFreeze-Installer-1.0.0rc10.run.sha256
```

Sonuc su olmali:

```text
CachyFreeze-Installer-1.0.0rc10.run: OK
```

`FAILED` gorurseniz kurulum yapmayin. Dosyalari silip tekrar indirin.

Calistirma izni verin:

```bash
chmod 0755 CachyFreeze-Installer-1.0.0rc10.run
```

## 5. Workstation'i Kur

Installer'i `sudo` ile baslatmayin:

```bash
cd "$HOME/CachyKurulum"
./CachyFreeze-Installer-1.0.0rc10.run
```

Acik pencerede:

1. PolicyKit yonetici onayini verin.
2. **Employee username** alanina calisan kullanici adini yazin.
3. **INSTALL / REPAIR** dugmesine basin.
4. Islem bitene kadar pencereyi kapatmayin.

Bu adim Google Chrome, LibreOffice, AnyDesk, Zoiper, MicroSIP/Wine,
masaustu kisayollari, login ekraninda calisan hesabinin secili gelmesini ve
60/120 dakika bosta kalma politikasini kurar.

Basarili sonuc:

```text
OVERALL: PASS
READY FOR FREEZE
```

FAIL gorurseniz **INSTALL / REPAIR** dugmesine tekrar basin.

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
./CachyFreeze-Installer-1.0.0rc10.run
```

Sonra:

1. **Employee username** alanina calisan kullanici adini yazin.
2. **CHECK** dugmesine basin.

Devam etmek icin sonuc mutlaka su olmali:

```text
OVERALL: PASS
Ready for freeze: YES
```

Bu kontrol uygulama icinde detayli PASS/FAIL raporu olarak gorunur. Login
ekraninda calisan hesabi secili gelmiyorsa veya autologin aciksa kontrol FAIL
verir. 60 dakikada kilit ve toplam 120 dakikada poweroff politikasi da bu
kontrole dahildir.

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
3. Login ekraninda calisan hesabinin secili geldigini kontrol edin.
4. Calisan hesabinda gecici bir dosya olusturun.
5. Bilgisayari yeniden baslatin.
6. Gecici dosyanin silindigini kontrol edin.

## Bosta Kalma Politikasi

Workstation kurulumu calisan oturumunda su kurali zorlar:

```text
60 dakika bosta     -> KDE oturumu kilitlenir
120 dakika toplamda -> sistem poweroff yapar
```

Sistem sleep inhibitor ile gercek suspend'i engeller. Bunun sebebi 120 dakikalik
poweroff zamaninin uyku sirasinda durup aktif FROZEN verilerinin makinede
kalmasini onlemektir.

Aktif verileri temizleyen guvenli adim poweroff/reboot sonrasi FROZEN `@active`
subvolume'unun Golden'dan yeniden olusturulmasidir.

## Mevcut CachyFreeze Kuruluysa

1. CachyFreeze'i acin.
2. **THAW COMPUTER** dugmesine basin.
3. **REBOOT NOW** ile yeniden baslatin.
4. Uygulama **THAWED** gosterince Workstation kurulum/repair yapin.
5. **CHECK** PASS olsun.
6. Calisan uygulamalarini elle test edin.
7. **FREEZE COMPUTER** yapin.
8. **REBOOT NOW** ile FROZEN moda donun.

## Ansible ile Uzaktan Toplu Yonetim (Filo Yonetimi)

Toplu kurulum ve bakim icin repo icinde `ansible/` klasoru vardir. Ansible
Master PC, Arch/CachyOS uzerinde repoyu clone ettikten sonra tek komutla
hazirlanir:

```bash
cd cachy-freeze/ansible
./setup-controller.sh
```

Bu betik Ansible, OpenSSH, sshpass ve Python paketlerini kurar; kontrol
makinesinde SSH anahtari yoksa olusturur. Sonra hedef PC'lere anahtari
gondermek icin `ssh-copy-id LocalAdm@IP` orneklerini gosterir.

Web arayuzu isteniyorsa Master PC'de su komut kullanilir:

```bash
cd cachy-freeze/ansible
./setup-controller.sh --with-semaphore
```

Bu secenek Docker ve Docker Compose'u da kurar, PostgreSQL 16 ile Semaphore UI
servisini baslatir ve arayuzu `http://localhost:3000` adresinde acar.
Semaphore Web Arayuzu ayni Ansible playbook'larini tek tikla calistirmak, canli
loglari izlemek ve gece bakimini cron ile zamanlamak icin kullanilir. Ayrintili
adimlar `ansible/SEMAPHORE-REHBERI.md` icindedir.

Envanter dosyasi:

```ini
[lab]
lab-01 ansible_host=192.0.2.10 employee_user=WRW21166

[production]
wrw-001 ansible_host=198.51.100.10 employee_user=WRW21166
```

Ortak ayarlar `ansible/inventory/group_vars/all.yml` icindedir. Baglanti
kullanicisi `LocalAdm` olur. Lab varsayilan olarak `batch_size: "100%"`,
production ise `batch_size: "20%"` kullanir; boylece 200+ PC tek seferde degil,
kontrollu dalgalar halinde bakima girer.

Sifir kurulum/lab onboarding:

```bash
ansible-playbook playbooks/provision.yml --limit lab --ask-become-pass
```

Bu akis `WRW21166` gibi calisan hesabini standart kullanici olarak olusturur,
admin gruplarina izin vermez, XDG dizinlerini acar, Workstation kurulumunu ve
`workstation-setup --check` kontrolunu gecirir, sonra CachyFreeze kurulumunu
yapip ilk FROZEN boot'u dogrular.

Rutin bakim:

```bash
ansible-playbook playbooks/maintenance.yml --limit production
```

Semaphore uzerinden ayni playbook hafta sonu 03:00 icin `0 3 * * 6,0` cron
ifadesiyle zamanlanabilir. Production grubunda varsayilan `batch_size: "20%"`
oldugu icin 200-300 PC kontrollu dalgalar halinde islenir.

Makine FROZEN ise playbook once su komutu calistirir:

```bash
cachy-freeze thaw --authorized
```

Bu komut GRUB ortaminda sadece bir sonraki acilis icin `cachy_remote_auth=1`
yazar. Boylece Ansible fiziksel klavyeden GRUB parolasi girmeden makineyi
THAWED moda alabilir. THAWED acilis dogrulamasi baslar baslamaz bayrak
`cachy_remote_auth=0` yapilir. Yani bu bir kalici sifresiz acilis degildir;
tek seferliktir ve acilista tuketilir.

Bakim sirasinda paket guncelleme, Workstation repair veya health check hata
verirse sistem dondurulmaz. Makine THAWED birakilir ve
`/var/log/cachy-freeze-ansible-failure.log` olusturulur.

Durum raporu:

```bash
ansible-playbook playbooks/status.yml --limit all
```

Acil durum icin sadece uzaktan thaw veya sadece freeze playbook'lari da vardir:

```bash
ansible-playbook playbooks/thaw.yml --limit wrw-001
ansible-playbook playbooks/freeze.yml --limit wrw-001
```
