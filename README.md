# CachyOS Kurumsal Laptop Kurulumu

CachyOS üzerinde şirket laptopu hazırlamak ve sistemi yeniden başlatmalarda
temiz bir **Frozen** duruma döndürmek için kullanılan kurulum paketidir.

Proje; UEFI, Btrfs ve GRUB düzenini doğrular, gerekli uygulamaları kurar,
yönetici yetkisi olmayan çalışan hesabını hazırlar ve Btrfs snapshot tabanlı
Frozen/Maintenance açılış düzenini kurar.

> [!CAUTION]
> Bu betikler açılış zincirini, initramfs'i, GRUB yapılandırmasını ve Btrfs alt
> birimlerini değiştirir. İlk kurulum mutlaka yedeği alınmış bir pilot cihazda
> ve cihazın başında yapılmalıdır.

## Belgeler

- [Ayrıntılı kurulum akışı](BASLA-BURADAN.md)
- [GitHub üzerinden Linux'ta çalışma](GITHUB-ILE-CALISMA.md)
- [Pilot cihaz kontrolleri](PILOT-NOTLARI.md)
- [Ekran gelmezse kurtarma notları](KURTARMA-EKRAN-GELMEZSE.txt)
- [USB ile kurulum (isteğe bağlı/eski yöntem)](USB-KURULUM.txt)

## Sistem nasıl çalışır?

| Mod | Amaç | Yeniden başlatma sonrası |
| --- | --- | --- |
| **THAWED (Maintenance)** | Kalıcı bakım, güncelleme ve yapılandırma | Değişiklikler korunur |
| **Golden** | Frozen sistemin yayımlanmış ana şablonu | Doğrudan kullanılmaz |
| **Frozen** | Çalışanın günlük, sıfırlanan sistemi | Yerel değişiklikler silinir |

Frozen sistem her açılışta Golden snapshot'tan yeniden oluşturulur. Yönetilen
çalışan ve `localadm` ev dizinleri de temiz şablonlarına döndürülür. Maintenance
modunda yapılan bir değişiklik kendiliğinden Frozen'a geçmez; bakım sonunda
`BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh` çalıştırılmalıdır.

## Gereksinimler

- UEFI açılış
- CachyOS ve KDE Plasma
- Btrfs kök dosya sistemi
- GRUB
- EFI bölümünün `/boot/efi` konumunda bağlı olması
- Ayrı bir `/boot` bölümünün **olmaması**
- İnternet bağlantısı
- `sudo` yetkili yerel yönetici hesabı

Betik, güvenli olmayan bir disk veya açılış düzeni görürse kurulumu durdurur.

## Projeyi GitHub'dan alma

Önerilen yöntem, projeyi Maintenance modunda veya henüz dondurulmamış temiz
CachyOS kurulumunda GitHub'dan klonlamaktır:

```bash
sudo pacman -S --needed git github-cli
gh auth login
mkdir -p ~/Projeler
cd ~/Projeler
gh repo clone q0xs/CachyOS-USB-Kurulum
cd CachyOS-USB-Kurulum
```

Depo özeldir; klonlama için `q0xs` hesabının veya izin verilmiş başka bir
GitHub hesabının kimlik doğrulaması gerekir.

## Hızlı kurulum

Normal kullanımda yalnızca aşağıdaki dört giriş betiği çalıştırılır:

1. Ana kurulumu başlat:

   ```bash
   bash ./ADIM-01-KURULUMU-BASLAT.sh
   ```

2. Çalışan hesabında uygulamaları ve ses/kamera erişimini test et. Ayrıcalıklı
   bir masaüstü işleminin `localadm` parolasını sorduğunu doğrula.

3. Kurulumu tamamla ve Golden sistemi yayımla:

   ```bash
   bash ./ADIM-02-KURULUMU-TAMAMLA.sh
   sudo reboot
   ```

4. İlk Frozen testini yap. Oluşturduğun geçici bir dosyanın yeniden başlatmadan
   sonra silindiğini doğrula.

`installer/` ve `deepfreeze/` altındaki dosyalar normal kurulum sırasında tek
tek çalıştırılmamalıdır. Tüm adımlar ve beklenen ekranlar için
[`BASLA-BURADAN.md`](BASLA-BURADAN.md) izlenmelidir.

## Bakım

Frozen sistemden sonraki açılışı Maintenance yapmak için:

```bash
bash ./BAKIM-01-COZ.sh
sudo reboot
```

Maintenance modunda bakım tamamlandıktan sonra değişiklikleri yeni Golden
olarak yayımlamak için:

```bash
bash ./BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh
sudo reboot
```

GRUB moda göre yalnızca tek giriş gösterir: **FROZEN** veya **THAWED**.
FROZEN parola istemez. THAWED seçildiğinde `cachyadmin` kullanıcısı ve kurulum
sırasında belirlenen GRUB parolası istenir.

## Proje yapısı

```text
.
├── ADIM-01-KURULUMU-BASLAT.sh
├── ADIM-02-KURULUMU-TAMAMLA.sh
├── BAKIM-01-COZ.sh
├── BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh
├── deepfreeze/   # Btrfs, initramfs ve GRUB Frozen altyapısı
├── installer/    # Kurulum ve yayımlama adımları
├── policies/     # Yönetilen uygulama ilkeleri
├── user/         # Çalışan hesabı servisleri ve masaüstü girişleri
└── vendor/       # Çevrimdışı/denetlenmiş paketleme yardımcıları
```

## Statik kontroller

Bir Linux ortamında:

```bash
bash ./deepfreeze/tests/static.sh
```

Test; Bash sözdizimini, temel yapılandırmayı, masaüstü girişlerini, JSON
dosyasını ve sistemde bulunuyorsa ShellCheck/systemd doğrulamalarını çalıştırır.
Disk veya boot zincirini değiştiren entegrasyon testleri yalnızca ayrılmış test
ortamında çalıştırılmalıdır.

## Güvenlik ve yedekleme

- GitHub yedeği proje dosyalarını korur; çalışır durumdaki laptopun disk
  yedeğinin veya önyüklenebilir kurtarma medyasının yerini tutmaz.
- Parola, erişim anahtarı, cihaz UUID'si ve gerçek kullanıcı verilerini depoya
  eklemeyin.
- Frozen modda yapılan ve GitHub'a gönderilmeyen değişiklikler yeniden
  başlatmada kaybolur.
- `@`, `@golden` veya `@active` Btrfs alt birimlerini elle silmeyin.
- `btrfs check --repair` komutunu uzman yönlendirmesi olmadan çalıştırmayın.
- Dondurma veya yayımlama sırasında bilgisayarın gücünü kesmeyin.
