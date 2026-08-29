# CachyOS iş bilgisayarı kurulumu

Bu rehber, kurulumu yapacak kişinin GitHub deposunu klonlamadan ve GitHub
hesabına giriş yapmadan CachyWorkstation Setup ile CachyFreeze'i indirip doğru
sırayla kurması içindir. Komutları sırayla Konsole'a kopyalayıp çalıştırın.

## İki ayrı program

- **CachyWorkstation Setup:** Çalışan uygulamalarını, masaüstü kısayollarını,
  MicroSIP/Wine kurulumunu ve 60/120 dakika boşta kalma politikasını hazırlar.
- **CachyFreeze:** Test edilmiş sistemi en son dondurur. Workstation Setup'ı
  kurmaz veya çalıştırmaz.

> [!IMPORTANT]
> Önce Workstation Setup, uygulama testleri ve sağlık kontrolü; en son
> CachyFreeze kurulumu yapılmalıdır. Workstation kurulumu veya onarımı FROZEN
> durumdayken kesinlikle çalıştırılmamalıdır.

## Başlamadan önce

Şunların hazır olduğundan emin olun:

- CachyOS, KDE Plasma, UEFI, GRUB ve Btrfs `@` düzeni kurulu olmalıdır.
- Yönetici hesabı hazır olmalıdır.
- Çalışan hesabı elle oluşturulmuş olmalıdır. Örnek: `wrw1166`.
- Çalışan hesabında `sudo`, `wheel` veya başka yönetici yetkisi olmamalıdır.
- Bilgisayar internete ve elektriğe bağlı olmalıdır.
- Kurtarma medyası ve geri yüklenebilir yedek hazır tutulmalıdır. Yayımlanan iki
  paket de şu anda ön sürümdür.

CachyFreeze bu bilgisayarda zaten kuruluysa önce CachyFreeze'i açın, **THAW
COMPUTER** seçeneğine basın ve **REBOOT NOW** ile yeniden başlatın. Devam etmeden
önce uygulamanın **THAWED** gösterdiğini kontrol edin.

## 1. Sistemi güncelleyin ve indirme aracını kurun

Konsole'u yönetici hesabında açın ve çalıştırın:

```bash
sudo pacman -Syu --needed curl
```

Komut tamamlandıktan sonra açık çalışmalarınızı kaydedin ve bilgisayarı yeniden
başlatın:

```bash
sudo systemctl reboot
```

CachyFreeze önceden kuruluysa yeniden açıldıktan sonra hâlâ **THAWED** durumda
olduğunu kontrol edin.

## 2. İki kurulum paketini doğrudan indirin

Yönetici hesabında tekrar Konsole açın. Aşağıdaki bloğun tamamını kopyalayıp
çalıştırın:

```bash
mkdir -p "$HOME/CachyKurulum"
cd "$HOME/CachyKurulum"

curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/workstation-v1.0.0/CachyWorkstation-Setup-1.0.0.run"
curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/workstation-v1.0.0/CachyWorkstation-Setup-1.0.0.run.sha256"
curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc6/CachyFreeze-Installer-1.0.0rc6.run"
curl --fail --location --retry 3 --remote-name \
  "https://github.com/q0xs/cachy-freeze/releases/download/v1.0.0rc6/CachyFreeze-Installer-1.0.0rc6.run.sha256"
```

Bu işlem için GitHub hesabı, `git clone` veya kaynak kod deposu gerekmez.

## 3. İndirilen dosyaları doğrulayın

```bash
cd "$HOME/CachyKurulum"
sha256sum --check CachyWorkstation-Setup-1.0.0.run.sha256
sha256sum --check CachyFreeze-Installer-1.0.0rc6.run.sha256
```

İki satır da `OK` ile bitmelidir:

```text
CachyWorkstation-Setup-1.0.0.run: OK
CachyFreeze-Installer-1.0.0rc6.run: OK
```

`FAILED` görürseniz hiçbir kurulum dosyasını çalıştırmayın. Dosyaları yeniden
indirin ve doğrulamayı tekrarlayın.

Doğrulama başarılıysa çalıştırma izni verin:

```bash
cd "$HOME/CachyKurulum"
chmod 0755 CachyWorkstation-Setup-1.0.0.run
chmod 0755 CachyFreeze-Installer-1.0.0rc6.run
```

## 4. Workstation uygulamalarını kurun

Aşağıdaki komut kullanıcı adını sorar. Örneğin `wrw1166` yazıp Enter'a basın:

```bash
cd "$HOME/CachyKurulum"
read -r -p "Çalışan kullanıcı adı: " CALISAN_KULLANICI
sudo ./CachyWorkstation-Setup-1.0.0.run "$CALISAN_KULLANICI"
```

Kurulum internetten gerekli CachyOS paketlerini ve doğrulanan resmî uygulama
dosyalarını indirir. İşlem tamamlanana kadar Konsole'u kapatmayın.

Başarılı sonuçta şunları görmelisiniz:

```text
OVERALL: PASS
READY FOR FREEZE
```

Bir bölüm `FAIL` olursa henüz CachyFreeze kurmayın. İnternet bağlantısını ve
ekrandaki hata nedenini kontrol ettikten sonra onarım çalıştırın:

```bash
cd "$HOME/CachyKurulum"
read -r -p "Çalışan kullanıcı adı: " CALISAN_KULLANICI
sudo ./CachyWorkstation-Setup-1.0.0.run --repair "$CALISAN_KULLANICI"
```

## 5. Uygulamaları çalışan hesabında test edin

Yönetici oturumundan çıkın ve çalışan hesabıyla giriş yapın. Masaüstünden veya
uygulama menüsünden aşağıdakileri tek tek açın:

1. Google Chrome
2. LibreOffice
3. AnyDesk
4. Zoiper
5. MicroSIP

Her uygulamanın açıldığını kontrol edin. Chrome ile bir internet sayfası açın,
LibreOffice'te boş bir belge oluşturun ve diğer üç uygulamanın ana ekranının
hatasız açıldığını doğrulayın.

### 60/120 dakika boşta kalma testi

Önce tüm çalışmalarınızı kaydedin. Fareye ve klavyeye hiç dokunmayın:

- Yaklaşık 60 dakika sonra oturum kilitlenmelidir.
- Kilidi açmayın ve hiçbir tuşa basmayın.
- İlk boşta kalma anından toplam 120 dakika sonra bilgisayar kapanmalıdır.

Bilgisayarı tekrar açın. Kullanıcı 60. dakikadan sonra geri dönüp kilidi açarsa
önceki süre iptal edilir; bir sonraki boşta kalma süresi yeniden sıfırdan
başlar.

## 6. Son sağlık kontrolünü çalıştırın

Yönetici hesabıyla giriş yapın ve çalıştırın:

```bash
cd "$HOME/CachyKurulum"
read -r -p "Çalışan kullanıcı adı: " CALISAN_KULLANICI
sudo ./CachyWorkstation-Setup-1.0.0.run --check "$CALISAN_KULLANICI"
```

Devam etmek için sonuç mutlaka şu olmalıdır:

```text
OVERALL: PASS
Ready for freeze: YES
```

Tek bir `FAIL` bile varsa CachyFreeze ile dondurmayın. Önce `--repair`
çalıştırın, uygulamaları tekrar test edin ve `--check` komutunu yeniden
çalıştırın.

## 7. CachyFreeze'i en son kurun

Bu bölüm yeni, henüz CachyFreeze kurulmamış bilgisayar içindir. Yönetici
hesabının grafik oturumunda çalıştırın:

```bash
cd "$HOME/CachyKurulum"
./CachyFreeze-Installer-1.0.0rc6.run
```

Bu dosyayı `sudo` ile başlatmayın. Açılan grafik kurulum ekranında:

1. İstenen PolicyKit yönetici onayını verin.
2. 12-256 karakterlik GRUB bakım parolasını iki kez girin.
3. **INSTALL CACHYFREEZE** seçeneğine basın.
4. Başarı mesajı gelene kadar bilgisayarı kapatmayın.
5. Açık çalışmalarınızı kaydedip **REBOOT NOW** seçeneğine basın.

İlk kurulum test edilmiş sistemi Golden olarak kaydeder ve sonraki açılışı
FROZEN olarak ayarlar.

### CachyFreeze zaten kuruluysa

Kurulum dosyasını tekrar çalıştırmayın. Son sağlık kontrolü `PASS` olduktan
sonra kurulu CachyFreeze uygulamasını açın:

1. **FREEZE COMPUTER** seçeneğine basın.
2. İşlem başarıyla tamamlanana kadar bekleyin.
3. **REBOOT NOW** seçeneğine basın.

## 8. FROZEN durumunu doğrulayın

Yeniden başlatmadan sonra CachyFreeze uygulamasının **FROZEN** gösterdiğini
kontrol edin. Çalışan hesabıyla masaüstünde geçici bir dosya oluşturun, tekrar
yeniden başlatın ve dosyanın kaybolduğunu doğrulayın.

Kurulum ancak aşağıdakilerin tamamı doğruysa bitmiştir:

- Beş uygulama çalışan hesabında açılıyor.
- Çalışan hesabında yönetici yetkisi yok.
- Workstation sağlık kontrolü `OVERALL: PASS` gösteriyor.
- 60 dakika sonra ekran kilitleniyor.
- Toplam 120 dakika boşta kalınca bilgisayar kapanıyor.
- Bilgisayar FROZEN açılıyor ve geçici değişiklikler yeniden başlatmada
  siliniyor.

> [!CAUTION]
> Workstation kurulumu, `--repair` veya sistem güncellemesi gerekiyorsa önce
> CachyFreeze içinden **THAW COMPUTER** seçin ve yeniden başlatın. Bu işlemleri
> hiçbir zaman FROZEN `@active` üzerinde yapmayın.
