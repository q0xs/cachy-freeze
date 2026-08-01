# CachyOS Kurumsal Laptop Kurulumu — Türkçe Rehber

Bu belge ayrıntılı Türkçe kurulum sırasıdır. Projenin İngilizce genel
açıklaması ve güvenlik uyarıları için `README.md` dosyasını da oku.

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

## Yalnızca Cachy Freeze masaüstü uygulamasını kurmak

Kurumsal uygulamalar ve çalışan hesabı olmadan yalnızca grafik dondurma
yöneticisini birden fazla CachyOS bilgisayara kurmak için depoyu klonladıktan
sonra çalıştır:

```bash
bash ./03-ALTERNATIF-SADECE-FREEZE-UYGULAMASI.sh
```

Bu dosya tam kurulumun `01` ve `02` adımlarına alternatiftir; tam kurulumdan
sonra ayrıca çalıştırılmaz.

Kurucu her bilgisayarın Btrfs UUID'sini kendisi algılar. İşlem yalnızca UEFI,
Btrfs ve GRUB kullanan, EFI bölümü `/boot/efi` konumunda bağlı olan ve ayrı
`/boot` bölümü bulunmayan CachyOS kurulumlarında devam eder. Uygulama menüsünde
**Cachy Freeze Yöneticisi** adıyla görünür:

- **Erit:** Sonraki açılışı kalıcı bakım moduna geçirir.
- **Dondur:** Bakım sistemini önce yeni Golden snapshot olarak kaydeder,
  ardından sonraki açılışı sıfırlanan Frozen moda geçirir.

PyQt6 arayüzü mevcut modu bir durum kartında gösterir; işlem sırasında ilerleme
göstergesi sunar. Her iki işlem yönetici parolası ister, sonucunu gösterir ve
ardından yeniden başlatmayı teklif eder.

Kurulum tamamlanıp yeni sistem açıldıktan sonra günlük yönetimi uygulama
menüsündeki **Cachy Freeze Yönetim Merkezi** üzerinden yap.

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
bash ./01-TAM-KURULUMU-BASLAT.sh
```

Bu adım internetten sistem güncellemelerini ve uygulamaları kurar. Ardından
çalışan hesabı için sırasıyla şunları sorar:

1. Kullanıcı adı
2. Görünen ad ve soyad
3. Parola ve parola tekrarı

Parola yazılırken ekranda görünmez. Çalışan hesabı yönetici olmaz fakat Chrome,
Slack, AnyDesk, LibreOffice, MicroSIP ve Zoiper'i normal şekilde açabilir.
Plasma ilk girişten itibaren Breeze Dark koyu temayla açılır. Çalışan hesabı
Windows'taki standart kullanıcı gibi kendi masaüstünü ve kullanıcı ayarlarını
değiştirebilir; terminal ve normal uygulama özellikleri yapay olarak
kapatılmaz. Sistem paketi kurma veya yönetim ayarı değiştirme gibi ayrıcalıklı
işlemler `localadm` yönetici parolasını ister.
Frozen modda `localadm` grafik oturum ekranında görünmez. Yönetici onayı
gereken masaüstü işlemleri “yetkisiz” diye kapanmak yerine mevcut `localadm`
parolasını ister. Çalışan ve `localadm` ev dizinleri her Frozen açılışta temiz
şablonlarına döner. THAWED modda `localadm` normal tam yetkili hesabıdır.

## 4. Bilgisayarı yeniden başlatmadan uygulamaları kontrol et

Ana kurulum bitince sistem Maintenance modunda kalır. Çalışan hesabına geçip
özellikle şunları kontrol et:

- Google Chrome açılıyor ve internet sitelerine giriyor.
- Slack açılıyor.
- AnyDesk açılıyor.
- LibreOffice açılıyor.
- MicroSIP ve Zoiper açılıyor.
- Mikrofon, hoparlör ve kulaklık giriş/çıkışları çalışıyor.
- Ayrıcalıklı bir masaüstü işlemi `localadm` parolasını soruyor.
- Çalışan hesabı doğrudan `sudo` grubunda bulunmuyor.
- Plasma ve uygulamalar koyu temayla açılıyor.
- Çalışan kendi kullanıcı ayarlarını değiştirebiliyor.

Bir sorun varsa henüz dondurma yapma.

Kontroller bitince çalışan masaüstündeki **Kurulumu Tamamlamak İçin Çıkış Yap**
kısayoluna tıkla. Giriş ekranından `localadm` hesabını seç ve kendi yönetici
parolanla giriş yap.

## 5. Kurulumu tamamla

Maintenance hesabına dön ve çalıştır:

```bash
bash ./02-TAM-KURULUMU-TAMAMLA.sh
```

Dosya önce onay ister; ardından GRUB parolasını ayarlar, çalışan hesabında test
edilen ayarları sıfırlama şablonuna aktarır, Golden'ı yayınlar ve sonraki açılışı
Frozen yapar. GRUB kullanıcı adı `cachyadmin` olur. Belirlediğin parolayı güvenli
bir yerde sakla. GRUB moda göre tek bir **FROZEN** veya **THAWED** girişi
gösterir. FROZEN parola istemez; THAWED kullanıcı adı/parola ister. İşlem
bitince `sudo reboot` komutunu elle çalıştır.

GRUB'da Frozen açılmalı. Çalışan hesabında küçük bir deneme dosyası oluştur,
yeniden başlat ve dosyanın silindiğini doğrula.

## Sonradan bakım yapmak

Günlük yönetimde terminal gerekmez. **Cachy Freeze Yönetim Merkezi** içinden:

1. Ayarlar sayfasında kalıcı THAWED veya yalnızca bir kez THAWED seç.
2. Uygulamanın sunduğu yeniden başlatma onayını kullan.
3. Bakım kökünde Güncellemeler sayfasından denetim ve güncellemeyi çalıştır.
   Uygulama önce geri dönüş snapshotı alır ve başarılı sonuçta Golden'ı yayınlar.
4. Snapshot sayfasından istersen açıklamalı ek snapshot oluştur, karşılaştır veya
   doğrula.
5. Dashboard/Ayarlar üzerinden FROZEN seçip uygulamanın yeniden başlatma
   onayını kullan.

Kullanıcı oluşturma, parola sıfırlama, kilitleme, otomatik giriş, snapshot
rollback/export/import, audit logları ve saklama politikası da aynı GUI içinden
yönetilir. Bootstrap betikleri yalnızca ilk teknisyen kurulumunun parçasıdır.

## Önemli

- İlk Frozen testi tamamlanana kadar proje klonunu ve önyüklenebilir CachyOS
  kurtarma medyasını hazır tut.
- GitHub proje dosyalarının yedeğidir; açılmayan bir cihaz için önyüklenebilir
  kurtarma medyasının yerini tutmaz.
- GRUB parolasını unutma.
- Btrfs snapshot disk arızasına karşı yedek değildir.
- Ekran açılmazsa `KURTARMA-EKRAN-GELMEZSE.txt` dosyasını oku.
