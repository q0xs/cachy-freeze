# CachyOS Kurumsal Laptop Kurulumu

Bu belge ayrıntılı kurulum sırasıdır. Projenin genel açıklaması ve güvenlik
uyarıları için önce `README.md` dosyasını oku.

Önerilen yöntem projeyi GitHub'dan almaktır. USB ile kopyalama yalnızca internet
erişimi olmayan kurulumlar için isteğe bağlı bir alternatiftir. Klasör içindeki
betikleri tek tek seçmek yerine aşağıdaki sırayı kullan.

## 1. CachyOS'u temiz kur

CachyOS kurulumunda:

- UEFI açılışı kullan.
- Dosya sistemi olarak **Btrfs** seç.
- Açılış yöneticisi olarak **GRUB** seç.
- EFI bölümünü `/boot/efi` konumuna bağla.
- Ayrı bir `/boot` bölümü oluşturma.
- Yönetici hesabını oluştur ve internete bağlan.

Kurulum tamamlanıp yeni sistem açıldıktan sonra `localadm` hesabında terminali
aç.

## 2. Projeyi GitHub'dan al

```bash
sudo pacman -S --needed git github-cli
gh auth login
mkdir -p ~/Projeler
cd ~/Projeler
gh repo clone q0xs/CachyOS-USB-Kurulum
cd CachyOS-USB-Kurulum
```

Depo özel olduğundan GitHub hesabının erişim izni olmalıdır. İnternet
kullanılamıyorsa proje klasörünün tamamını USB'den kopyalayıp terminali o
klasörde açabilirsin.

Doğru klasörde olduğunu kontrol et:

```bash
pwd
```

Çıktının sonu `CachyOS-USB-Kurulum` olmalıdır.

## 3. Ana kurulumu çalıştır

```bash
bash ./ADIM-01-KURULUMU-BASLAT.sh
```

Bu adım internetten sistem güncellemelerini ve uygulamaları kurar. Ardından
çalışan hesabı için sırasıyla şunları sorar:

1. Kullanıcı adı
2. Görünen ad ve soyad
3. Parola ve parola tekrarı

Parola yazılırken ekranda görünmez. Çalışan hesabı yönetici olmaz fakat Chrome,
Slack, AnyDesk, LibreOffice, MicroSIP ve Zoiper'i normal şekilde açabilir.
Frozen modda `localadm` oturum ekranında görünmez ve bu hesapla oturum
açılamaz. Yönetici onayı gereken bir işlem olursa mevcut `localadm` parolası
kullanılabilir. Maintenance modda `localadm` normal tam yetkili hesabıdır.

## 4. Bilgisayarı yeniden başlatmadan uygulamaları kontrol et

Ana kurulum bitince sistem Maintenance modunda kalır. Çalışan hesabına geçip
özellikle şunları kontrol et:

- Google Chrome açılıyor ve internet sitelerine giriyor.
- Slack açılıyor.
- AnyDesk açılıyor.
- LibreOffice açılıyor.
- MicroSIP ve Zoiper açılıyor.
- Çalışan hesabı `sudo` kullanamıyor.

Bir sorun varsa henüz dondurma yapma.

Kontroller bitince çalışan masaüstündeki **Kurulumu Tamamlamak İçin Çıkış Yap**
kısayoluna tıkla. Giriş ekranından `localadm` hesabını seç ve kendi yönetici
parolanla giriş yap.

## 5. Kurulumu tamamla

Maintenance hesabına dön ve çalıştır:

```bash
bash ./ADIM-02-KURULUMU-TAMAMLA.sh
```

Dosya önce onay ister; ardından GRUB parolasını ayarlar, çalışan hesabında test
edilen ayarları sıfırlama şablonuna aktarır, Golden'ı yayınlar ve sonraki açılışı
Frozen yapar. GRUB kullanıcı adı `cachyadmin` olur. Belirlediğin parolayı güvenli
bir yerde sakla. Frozen girişi parola istemez; Maintenance girişi kullanıcı
adı/parola ister. İşlem bitince `sudo reboot` komutunu elle çalıştır.

GRUB'da Frozen açılmalı. Çalışan hesabında küçük bir deneme dosyası oluştur,
yeniden başlat ve dosyanın silindiğini doğrula.

## Sonradan bakım yapmak

GRUB'dan Maintenance seçip `cachyadmin` ve GRUB parolasıyla açabilirsin.
Güncelleme veya ayar değişikliğinden sonra:

```bash
bash ./BAKIM-02-DEGISIKLIKLERI-YAYINLA.sh
sudo reboot
```

Bu bakım dosyası hem Golden'ı yayınlar hem sonraki açılışı Frozen yapar.

Frozen içindeyken sonraki açılışları kalıcı olarak Maintenance yapmak istersen:

```bash
bash ./BAKIM-01-COZ.sh
sudo reboot
```

## Önemli

- İlk Frozen testi tamamlanana kadar proje klonunu ve önyüklenebilir CachyOS
  kurtarma medyasını hazır tut.
- GitHub proje dosyalarının yedeğidir; açılmayan bir cihaz için önyüklenebilir
  kurtarma medyasının yerini tutmaz.
- GRUB parolasını unutma.
- Btrfs snapshot disk arızasına karşı yedek değildir.
- Ekran açılmazsa `KURTARMA-EKRAN-GELMEZSE.txt` dosyasını oku.
