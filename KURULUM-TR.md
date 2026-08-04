# CachyOS Kurumsal Laptop Kurulumu — Türkçe Rehber

Bu belge ayrıntılı Türkçe kurulum sırasıdır. Projenin İngilizce genel
açıklaması ve güvenlik uyarıları için `README.md` dosyasını da oku.

Önerilen yöntem projeyi GitHub'dan alıp tek grafik kurulum uygulamasını açmaktır.
USB ile kopyalama yalnızca internet erişimi olmayan kurulumlar için isteğe bağlı
bir alternatiftir. Normal akışta terminal veya numaralı betikler kullanılmaz.

## 1. CachyOS'u temiz kur

CachyOS kurulumunda:

- UEFI açılışı kullan.
- Dosya sistemi olarak **Btrfs** seç.
- Açılış yöneticisi olarak **GRUB** seç.
- EFI bölümünü `/boot/efi` konumuna bağla.
- Ayrı bir `/boot` bölümü oluşturma.
- Yönetici hesabını oluştur ve internete bağlan.

## 2. Projeyi terminal kullanmadan al

Depo özel olduğundan erişim izni olan GitHub hesabıyla web tarayıcısında oturum
aç. Depo sayfasından **Code → Download ZIP** seçeneğini kullan ve ZIP dosyasını
normal bir klasöre çıkar. İnternet olmayan pilotta aynı proje klasörünün tamamını
USB'den kopyalayabilirsin.

Git bilen teknisyenler isterse klonlama kullanabilir; ancak normal kurulumda
terminal açmak veya `git`, `gh`, `sudo` komutları yazmak gerekmez.

## 3. Tek kurulum uygulamasını aç

Çıkardığın proje klasöründeki **`CachyOS-Kurulum-Uygulamasi.desktop`** dosyasına
çift tıkla. Plasma dosyaya güvenilip güvenilmediğini sorarsa **Çalıştır / Güven**
seçeneğini onayla.

İlk açılışta yalnızca PyQt6 grafik çalışma zamanı eksikse yüklenir. Bu işlem ve
sonraki ayrıcalıklı adımlar standart PolicyKit penceresinde `localadm` parolasını
ister. Parolalar terminalde, süreç argümanlarında veya loglarda gösterilmez.

Çalışan oturumu açılırken QMK/VIA klavye sorgusu, ayrık GPU algılama, etkin
kullanıcının ağ bağlantısı veya pil sınırı okuma gibi Plasma başlangıç işlemleri
`localadm` parolası sormamalıdır. Bunlar için uyarı çıkarsa parolayı otomatik
girmek yerine kurulumu durdur ve politika regresyonunu kaydet. Paket yönetimi,
sistem ayarı veya genel bir `pkexec` işlemi ise hâlâ `localadm` doğrulaması
istemelidir.

Uygulama açılınca soldaki **Kurulum** sayfasına gelir. Bundan sonraki ilk kurulum,
test, Golden yayınlama, FROZEN ayarı ve yeniden başlatma aynı uygulama üzerinden
yapılır.

## 4. Ön kontrolü çalıştır

**1. Sistem ön kontrolünü çalıştır** düğmesine bas. Uygulama aşağıdaki düzeni
doğrulamadan kurulum başlatmaz:

- CachyOS UEFI modunda açılmış olmalı.
- Kök dosya sistemi Btrfs ve kök alt birimi `@` olmalı.
- GRUB ve gerekli initramfs dosyaları bulunmalı.
- EFI bölümü `/boot/efi` konumuna bağlı olmalı.
- Ayrı bir `/boot` dosya sistemi bulunmamalı.

Ön kontrol hata verirse atlama veya betiği elle zorla çalıştırma. Uygulamadaki
hata ayrıntısını ve `/var/log/cachyos-workstation-install.log` dosyasını koru.

## 5. İş istasyonunu uygulamadan hazırla

Önyüklenebilir kurtarma medyası ve geri alınabilir yedek hazır kutusunu
işaretle. Aynı ekranda çalışan kullanıcı adını, görünen adını ve güçlü parolasını
gir; ardından **Tam kurulumu başlat** düğmesine bas.

Uygulama mevcut doğrulanmış kurulum motorunu kullanarak:

1. sistem paketlerini ve kurumsal uygulamaları kurar;
2. standart çalışan hesabını oluşturur ve `wheel`/`sudo` dışında tutar;
3. Chrome, Slack, AnyDesk, LibreOffice, MicroSIP ve Zoiper'i doğrular;
4. Btrfs, initramfs, GRUB, boot-health ve rollback altyapısını kurar;
5. yönetim uygulamasını sisteme yerleştirir;
6. ilk Golden snapshot'ı oluşturur ve sistemi test için THAWED bırakır.

İlerleme ve hatalar **Kurulum ilerlemesi ve hata ayrıntıları** alanında görünür.
İşlem sürerken bilgisayarı kapatma.

## 6. Uygulamaları ve hesabı canlı test et

Çalışan hesabına geçip özellikle şunları kontrol et:

- Google Chrome internete çıkıyor.
- Slack, AnyDesk, LibreOffice, MicroSIP ve Zoiper açılıyor.
- Mikrofon, hoparlör ve kulaklık giriş/çıkışları çalışıyor.
- Gerçek bir MicroSIP görüşmesi yapılabiliyor.
- Ayrıcalıklı bir masaüstü işlemi `localadm` parolasını soruyor.
- Çalışan hesabı `wheel` veya `sudo` grubunda bulunmuyor.
- Plasma ve uygulamalar koyu temayla açılıyor.

Bir sorun varsa FROZEN aşamasına geçme. `localadm` hesabına dön, **Cachy Freeze
Yönetim Merkezi → Kurulum** sayfasını aç ve hata kaydını koru.

Uygulama dosyasının veya komutunun varlığı yeterli değildir; her uygulamanın
gerçek penceresi çalışan hesabında açılmalıdır. Sanal makinedeki dummy/monitor
ses kaynağı gerçek mikrofon, hoparlör veya kulaklık kabulü değildir. Fiziksel
aygıt ve mümkünse gerçek arama doğrulanmadan ses kabul kutusunu işaretleme.

## 7. Aynı uygulamada kurulumu tamamla

Kurulum sayfasındaki üç canlı-test kutusunu onayla. Güçlü GRUB bakım parolasını
iki kez gir ve **Kurulumu tamamla ve FROZEN yap** düğmesine bas.

Bu üç kutu yalnız uygulama pencereleri, fiziksel ses/arama ve yönetici/standart
kullanıcı ayrımı gerçekten geçtiyse işaretlenir. Bir testi atlamak, VM sonucunu
fiziksel test saymak veya yalnız dosya varlığını kabul etmek desteklenmez.

Uygulama çalışan ile `localadm` ev şablonlarını günceller, GRUB bakım hesabını
`cachyadmin` olarak korur, yeni Golden'ı yayınlar ve sonraki açılışı FROZEN yapar.
Sonunda çıkan yeniden başlatma sorusunu onayla; ayrıca terminalden `sudo reboot`
yazmak gerekmez.

İlk FROZEN açılışta çalışan hesabında geçici bir dosya oluştur, uygulamadaki
**Yeniden başlat** düğmesini kullan ve dosyanın silindiğini doğrula.

## Eski numaralı dosyalar ne için?

`01`, `02`, `03`, `10` ve `11` numaralı kabuk girişleri geriye uyumluluk,
kurtarma ve uzman teşhisi için korunur. Normal ilk kurulumun veya günlük bakımın
parçası değildir. `installer/` ve `deepfreeze/` altındaki dosyaları tek tek
çalıştırma.

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
yönetilir. İlk kurulum ve sonraki bakım aynı uygulamada kalır.

## Önemli

- İlk Frozen testi tamamlanana kadar proje klonunu ve önyüklenebilir CachyOS
  kurtarma medyasını hazır tut.
- GitHub proje dosyalarının yedeğidir; açılmayan bir cihaz için önyüklenebilir
  kurtarma medyasının yerini tutmaz.
- GRUB parolasını unutma.
- Btrfs snapshot disk arızasına karşı yedek değildir.
- Fiziksel cihazda boot zinciri değişmeden önce AC güç, kurtarma USB'si, harici
  yedek ve geri dönüş noktası hazır olmalıdır.
- Golden yayını, pacman, mkinitcpio veya GRUB yazımı sırasında gücü kesme.
- `btrfs check --repair` çalıştırma; Golden/Active alt birimlerini elle silme.
- Ekran açılmazsa `KURTARMA-EKRAN-GELMEZSE.txt` dosyasını oku.
