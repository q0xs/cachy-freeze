# Development Handoff

Bu dosya Codex CLI için operasyonel devam kaynağıdır. Önce kök `AGENTS.md`
dosyasını, sonra bu dosyanın tamamını, `README.md`, `docs/architecture.md`,
`docs/installation.md`, `docs/development.md` ve `docs/pilot-checklist.md` dosyalarını oku.
Bir alt dizinde çalışırken o dizindeki daha özel `AGENTS.md` kurallarını da
uygula. Mevcut mimariyi ve çalışma ağacını incelemeden kod değiştirme.

## Her yeni Codex oturumunda başlangıç protokolü

1. `git status --short`, `git remote -v` ve `git log -3 --oneline` çıktısını
   incele. Kullanıcı değişikliklerini silme, stash etme veya ezme.
2. Hedefi açıkça sınıflandır: Windows host, VirtualBox VM veya fiziksel CachyOS
   laptop. Bir hedefteki snapshot, UUID, boot veya test sonucunu diğer hedefe
   taşınmış kabul etme.
3. Aşağıdaki doğrulanmış durumun yalnız bir devir notu olduğunu kabul et.
   UEFI/Btrfs/GRUB, kullanıcı, Golden/Active ve çalışma modu durumunu gerçek
   hedefte salt-okunur olarak yeniden doğrulamadan sistem değişikliği yapma.
4. Normal kullanıcıya terminal kurulum akışı veya `.sh` dosyası sunma. Kurulum
   yalnız `CachyOS-Kurulum-Uygulamasi.desktop` ve uygulamanın **Kurulum**
   sayfasından yürütülür. Terminal yalnız Codex'in repo, geliştirme, test, log ve
   salt-okunur teşhis işlemleri içindir.
5. Parola, token veya gizli bilgiyi isteme, tekrar etme, komut argümanına koyma,
   loglama, ekran görüntüsüne alma ya da repoya yazma. GUI'nin gizli parola
   alanlarını ve kapalı stdin kanalını kullan.

## Doğrulanmış durum — 4 Ağustos 2026

Güncel yerel QA hedefi `CachyFreeze-Clean-QA-20260804` adlı VirtualBox VM'dir.
Eski `CachyFreeze-QA-20260801` VM'si, eski snapshot adı/UUID'si veya eski test
sonucu bu hedefin ya da fiziksel laptopun durumu değildir.

Güncel VM'de yeniden doğrulanan düzen:

- kernel `7.1.5-1-cachyos`, Plasma, UEFI64;
- 80 GiB sanal disk, GPT, FAT32 EFI ve Btrfs kök;
- kök `/dev/sda2[/@]`, alt birim `@`;
- `/boot/efi` bağlı, ayrı `/boot` dosya sistemi yok;
- bootloader GRUB;
- `localadm` yönetici ve `wheel` üyesi;
- uygulamanın grafik ön kontrolü UEFI/Btrfs/`@`/EFI/GRUB kapısını geçti.

Kurulum yalnız grafik uygulamanın **Tam kurulumu başlat** akışıyla tamamlandı.
Güncel güvenli ara durum:

- `phase=provisioned`;
- yönetilen standart çalışan hesabı oluşturuldu ve `wheel`/`sudo` üyesi değil;
- Golden ve Active hazır;
- bekleyen Btrfs işlemi yok;
- GRUB bakım parolası finalize edilmedi;
- sistem THAWED bakım durumunda;
- finalize/FROZEN işlemi başlatılmadı.

Çalışan hesabında Google Chrome, Slack, AnyDesk, LibreOffice, Zoiper5 ve Wine
üzerinden MicroSIP gerçek pencereleri açıldı. Breeze Dark ve masaüstü
kısayolları doğrulandı. `sudo -n` reddedildi. Listede olmayan genel ayrıcalıklı
işlem hâlâ `localadm` doğrulaması istiyor.

VirtualBox yalnız sanal analog çıkış ve bu çıkışın monitor kaynağını sunuyor;
gerçek mikrofon/kulaklık ve gerçek test araması doğrulanmadı. Bu nedenle üç canlı
kabul kutusu işaretlenmedi ve finalize güvenlik kapısında bekliyor. Sanal/dummy
ses sonucunu fiziksel ses kabulü olarak raporlama.

Son host kontrolünde VirtualBox VM durumu `aborted` olarak görüldü. Bu durum
başarılı bir güç-kesintisi veya kurtarma testi değildir ve temiz kapanış kanıtı
olarak kullanılamaz. VM yeniden kullanılacaksa önce açılış modu, kök alt birimi,
bekleyen transaction, boot-health ve önceki/current journal hataları incelenmeli;
sağlık yeniden doğrulanmadan finalize, Golden yayını veya stres testi yapılmamalı.

Bu doküman güncellemesinden önceki repo checkpoint'i `9464b8b` commitiydi ve
GitHub Actions koşusu `30899113893` başarıyla tamamlanmıştı. Bunlar yalnız tarihî
devir kanıtıdır; güncel HEAD, Actions ve VM durumu her yeni oturumda yeniden
kontrol edilmelidir.

## Güncel devam noktası

1. Önce repo, hedef ve Dashboard/preflight durumunu yeniden doğrula. VM hedefi
   `aborted` görüldüğü için ilk açılışta boot-health ve journal kanıtını ayrıca
   kaydet.
2. VM ile devam edilecekse gerçek mikrofon, hoparlör ve kulaklığı VM'ye geçir;
   MicroSIP/Zoiper ses seçimini ve mümkünse gerçek test aramasını yap.
3. Fiziksel ses kabulü gerçekten geçmeden uygulamadaki üç kabul kutusunu
   işaretleme, GRUB bakım parolası alma veya finalize başlatma.
4. Kabul geçerse aşağıdaki finalize ve boot sırasını uygula. Geçmezse sistemi
   THAWED bırak, kanıtı raporla ve FROZEN/snapshot/stres adımlarına geçme.

## Bu turda yakalanıp düzeltilen gerçek hatalar

1. Masaüstü kurulum başlatıcısı pencere açmadan kod 0 ile çıkıyordu.
   `cachy_freeze_gui.main` için doğrudan modül giriş noktası eklendi ve olay
   döngüsünde kaldığı smoke testiyle doğrulandı.
2. Kullanıcı adı örneği nokta içeriyor, doğrulama ise noktayı reddediyordu.
   Örnek `ornek_kullanici` olarak düzeltildi.
3. `gtk2` 2026 Arch/CachyOS resmî depolarından kaldırılmıştı. Zoiper için GTK2
   AUR üzerinden ayrıcalıksız `makepkg` akışına alındı; gerekli resmî derleme
   bağımlılıkları eklendi.
4. Güncel AnyDesk AUR tarifi `lsb-release` istiyordu; resmî paket listesine
   eklendi.
5. Güncel CachyOS `HOOKS=(... filesystems fsck)` düzeninde initramfs hook ekleme
   ifadesi çalışmıyordu. `cachy-freeze`, `filesystems` önüne güvenli biçimde
   eklenecek şekilde düzeltildi.
6. Windows çalışma kopyasından taşınan AUR metinlerinin CRLF olabilmesi için
   `.gitattributes` LF kuralları genişletildi.
7. README içindeki kullanıcıya yönelik kabuk kurulum yolu kaldırıldı. Desteklenen
   kurulum girişi yalnızca `CachyOS-Kurulum-Uygulamasi.desktop` ve uygulamanın
   **Kurulum** sayfasıdır.
8. GitHub Ubuntu runner'ında PyQt6 için `libEGL.so.1` eksikliği ve `python -s`
   nedeniyle kullanıcı site paketinin görünmemesi yakalandı. Workflow'a `libegl1`
   eklendi, smoke testi normal modül çağrısına geçirildi ve hata çıktısı görünür
   yapıldı.
9. Dolphin'den açılan `.desktop` dosyasındaki KDE kaçışları başlatıcı yolunu
   bozuyordu. `%k`, `file://` ve boşluklu yol güvenli biçimde çözümlendi;
   `desktop-file-validate` CI kapısına eklendi (`0b73372`).
10. Çalışan hesabına uygulanan genel PolicyKit kuralı Plasma'nın QMK/VIA,
    ayrık GPU, ağ ve pil başlangıç sorgularını da yönetici doğrulamasına
    yükseltiyordu. Dağıtımın aktif yerel kullanıcıya zaten izin verdiği altı tam
    eylem kimliği dar izin listesine alındı; genel işlem hâlâ `localadm` istiyor
    (`9b7333f`).
11. ShellCheck'in `SC2155` değişken bildirimi ve dinamik GRUB config kaynağı
    uyarıları temizlendi; tam statik test yeniden geçirildi (`9464b8b`).
12. Kod incelemesinde kullanıcı yedeği geri yüklenirken parola hash'inin
    `useradd --password` süreç argümanına konduğu bulundu. Hash, doğrulanmış
    `chpasswd --encrypted` stdin kanalına taşındı ve ayırıcı/enjeksiyon birim
    testi eklendi. Bu düzeltmenin commit kimliği bu çalışma push edildikten
    sonra güncel GitHub geçmişinden doğrulanmalıdır.

Gerçek VM’de doğrulanan paketler:

- Google Chrome 150.0.7871.186;
- Slack 4.51.180;
- GTK2 2.24.33;
- Zoiper 5.6.13;
- AnyDesk 8.0.4;
- LibreOffice Fresh 26.2.5;
- Wine Staging 11.14;
- MicroSIP 3.22.12 ZIP ve içindeki `MicroSIP.exe` bütünlük kontrolü.

`qaemployee` standart kullanıcı olarak oluşturuldu; `wheel` üyesi değildir.
Audio/input/video grupları doğrulandı. Initramfs içinde
`usr/lib/cachy-freeze/cachy-freeze-reset` bulundu, GRUB yapılandırma kontrolü
geçti ve tek kurumsal menü girdisi üretildi. Btrfs aygıt hata sayaçlarının tamamı
sıfır, sağlık sonucu `healthy`, bozuk snapshot yoktur.

Otomatik test sonucu:

- Windows host: 31/31 Python testi, Ruff ve PyQt6 yedi sayfa smoke testi;
- CachyOS VM: 31/31 Python testi ve PyQt6 smoke testi;
- gerçek GUI başlatıcı olay döngüsü testi başarılı;
- gerçek UEFI/Btrfs/GRUB ön kontrolü ve ilk Golden yayını başarılı.

## Fiziksel CachyOS üzerinde devam sırası

Bu sırayı değiştirme. Her büyük adımdan sonra kanıtı kaydet ve hata varsa bir
sonraki adıma geçme.

### 1. Güvenlik kapısı ve repo doğrulaması

1. Bunun yedekli pilot laptop olduğunu kullanıcıyla doğrula. Kurtarma USB'si,
   AC güç ve geri alınabilir veri yedeği olmadan devam etme.
2. Host/VM/laptop ayrımını koru. Tüm Btrfs, GRUB, initramfs ve boot işlemleri
   yalnızca CachyOS hedefinde çalışsın.
3. `git status --short`, `git log -3 --oneline` ve `git remote -v` çıktısını
   incele. Kullanıcı değişikliklerini silme veya ezme.
4. `git pull --ff-only` kullan. Bu dosyayı ve README'yi tekrar oku.
5. UEFI, Btrfs `@`, `/boot/efi`, ayrı `/boot` bulunmaması ve `localadm` wheel
   üyeliğini salt-okunur komutlarla doğrula. Uyuşmazlıkta dur; ön kontrolü
   atlatma.
6. Statik analiz, Python birim testleri ve PyQt offscreen smoke testini çalıştır.
   Tüm sonuçları tarih ve commit ile bir QA raporuna yaz.

### 2. Yalnızca uygulamadan kurulum/hazırlama

1. Plasma'da `CachyOS-Kurulum-Uygulamasi.desktop` dosyasını aç. Normal kullanıcı
   için terminal kurulum yolu sunma.
2. **Kurulum** sayfasında ön kontrolü çalıştır ve gerçek sonucu kaydet.
3. Fiziksel laptop temizse uygulamadaki **Tam kurulumu başlat** akışını kullan.
   Parolaları hiçbir loga, komut argümanına, dosyaya veya rapora yazma.
4. Durum zaten `provisioned` ise hazırlamayı gereksiz yere tekrarlama; canlı
   kabul testine geç.

### 3. Finalize öncesi canlı kabul

THAWED bakım kökünde, önce `localadm`, sonra standart çalışan hesabıyla test et:

1. Chrome, Slack, AnyDesk, LibreOffice ve Zoiper'ı aç; yalnızca komut varlığını
   değil gerçek pencere açılışını doğrula.
2. MicroSIP'i Wine ile aç. Mikrofon, hoparlör, kulaklık seçimi ve mümkünse gerçek
   test araması yap. Sanal/dummy ses sonucunu fiziksel ses testi diye raporlama.
3. Standart kullanıcıdan ağ, tarih/saat veya paket gibi ayrıcalıklı bir masaüstü
   işlemi başlat. İşlem `localadm` parolasını istemeli; çalışan hesabı yönetici
   olmamalı.
4. `localadm` hesabının wheel/sudo çalışmasını; çalışan hesabının wheel/sudo
   dışında kalmasını doğrula.
5. Çalışan masaüstü kısayolları, Breeze Dark, oturum açma ve MicroSIP prefix
   izinlerini doğrula.
6. Ancak tüm maddeler gerçekten geçtiyse uygulamadaki üç canlı kabul kutusunu
   işaretle.

### 4. Uygulamadan finalize ve ilk boot zinciri

1. Kullanıcının seçtiği güçlü GRUB bakım parolasını uygulamadaki iki alana gir;
   parolayı isteme, kopyalama veya kaydetme.
2. **Kurulumu tamamla ve FROZEN yap** seçeneğini çalıştır. Golden yayını veya
   paket işlemi sırasında gücü kesme.
3. Uygulamanın yeniden başlatma teklifini kullan.
4. GRUB'da tek kurumsal girdiyi, FROZEN başlığı ve normal FROZEN açılışını
   doğrula. THAWED bakım seçiminin GRUB parolası istediğini ayrıca test et.
5. `journalctl -b`, `findmnt`, `/proc/cmdline`, boot-health ve uygulama Dashboard
   kanıtlarını kaydet.

### 5. FROZEN ve THAWED davranış testleri

1. FROZEN çalışan oturumunda benzersiz test dosyası ve ayar değişikliği oluştur;
   yeniden başlatınca kaybolduğunu doğrula.
2. FROZEN sırasında yönetilen `localadm` evinde kontrollü test izi oluştur;
   yeniden başlatınca şablondan döndüğünü doğrula.
3. Uygulamadan THAWED planla, yeniden başlat, test dosyası oluştur ve tekrar
   başlatınca kalıcı olduğunu doğrula.
4. **Yalnızca bir kez THAWED** akışını test et; sonraki boot THAWED, onu izleyen
   boot otomatik FROZEN olmalı.
5. Her boot sonrası mod, alt birim, Golden/Active varlığı, boot denemesi sayacı
   ve audit olaylarını karşılaştır.

### 6. Snapshot işlev testleri

Uygulamanın Snapshotlar sayfasından ve görünür sonuçlarını esas alarak:

1. İki açıklamalı snapshot oluştur.
2. İkisini de tam doğrula; metadata ve Btrfs send SHA-256 sonucunu kaydet.
3. Snapshotları karşılaştır ve beklenen test dosyası yolunu gör.
4. Bir snapshotı export et, aynı dosyayı import et ve tekrar tam doğrula.
5. Export dosyasının kopyasında tek byte değiştir; importun checksum hatasıyla
   reddedildiğini doğrula. Gerçek Golden/Active alt birimlerini bozma.
6. Bir snapshotı sil ve katalogdan kalktığını doğrula.
7. Sağlıklı test snapshotına rollback planla, yeniden başlat ve içerik/mod
   doğrulaması yap.

### 7. Güncelleme ve kullanıcı yaşam döngüsü

1. Güncellemeler sayfasında salt-okunur kontrol yap.
2. THAWED modda korumalı güncellemeyi çalıştır. Öncesinde rollback snapshotı,
   sonrasında paket doğrulaması ve yeni Golden oluştuğunu kanıtla.
3. Geçici standart kullanıcı oluştur; parola değiştir, kilitle/aç, autologin
   ayarla/kaldır, yedekleyerek sil ve yedekten geri yükle.
4. Hiçbir standart kullanıcının wheel/sudo kazanmadığını ve Polkit'in
   `localadm` istediğini her kritik noktada doğrula.

### 8. Stres, performans ve dayanıklılık testleri

Önce sağlıklı Golden, kurtarma medyası ve geri dönüş snapshotı bulunmalı.

1. **25 snapshot stresi:** kontrollü küçük dosya değişiklikleriyle 25 snapshot
   oluştur; her birini metadata doğrulamasından geçir, seçili örneklerde tam
   Btrfs doğrulaması yap, retention cleanup sonucunu doğrula.
2. **İşlem kilidi:** uzun doğrulama sürerken ikinci yazma işlemi başlat; güvenli
   biçimde reddedilmeli ve katalog bozulmamalı.
3. **10 boot çevrimi:** FROZEN/THAWED/tek-sefer THAWED sırasını 10 yeniden
   başlatmada çalıştır. Her çevrimde boot süresi, mod, hata sayacı ve journal
   hatalarını kaydet.
4. **Bellek:** uygulamayı aç/kapat, 30 yenileme ve sayfa geçişi yap. Başlangıç ve
   bitiş RSS/PSS, sistem boş belleği ve süreç sayısını kaydet; sürekli büyüme,
   zombie veya kilitli yardımcı süreç bırakma varsa hata aç.
5. **Disk:** test öncesi/sonrası `btrfs filesystem usage`, `btrfs device stats`,
   snapshot exclusive/apparent boyutları ve export alanını kaydet. Beklenmeyen
   sınırsız büyüme olmamalı.
6. **Uzun kullanım:** en az 2 saat çalışan oturum, uygulama yenilemeleri,
   MicroSIP/Chrome/Slack kullanımı ve otomatik snapshot timer çalışmasını izle.
7. **Beklenmeyen kapanma:** yalnızca kullanıcı açıkça onaylarsa ve sağlıklı
   Golden + harici yedek varsa yap. İlk denemeyi VM'de uygula. Fiziksel cihazda
   Golden yayını, pacman veya initramfs yazımı sırasında asla güç kesme.
8. **Boot kurtarma:** başarısız boot sayacı ve önceki sağlıklı Golden'a otomatik
   dönüşü önce VM'de test et. Fiziksel laptopta EFI/GRUB dosyalarını bilerek
   bozma; kurtarma testi için kullanıcıdan ayrıca açık onay al.

### 9. Son kalite kapısı ve GitHub

1. Tüm testleri yeniden çalıştır; Ruff, format kontrolü, Bash syntax,
   ShellCheck, systemd verify, Python testleri ve GUI smoke sıfır hatalı olmalı.
2. `journalctl -b -p err`, Btrfs device stats, boot-health, snapshot health,
   bellek ve disk sonuçlarını incele. VirtualBox grafik sürücüsü uyarılarını
   fiziksel laptop sonucu olarak değerlendirme.
3. Gerçek test sonuçlarını yeni tarihli bir QA raporuna yaz; geçen, kalan ve
   koşullu testleri açıkça ayır. Yapılmamış testi geçti diye yazma.
4. Kullanıcı değişikliklerini koru. İlgili dosyaları açıkça stage et, diff'i
   incele, kısa commit oluştur ve kullanıcı tercihi değişmediyse PR açmadan
   doğrudan `main` dalına push et.
5. GitHub Actions sonucunu doğrula. Başarısızsa logu incele, düzelt ve yeniden
   çalıştır.

## Fiziksel CachyOS ayrıntılı kabul matrisi

Bu matris fiziksel pilotta uygulanacak asgari kanıt sözleşmesidir. Normal
kullanıcının bütün kurulum ve bakım işlemleri GUI'de kalır. Aşağıdaki komutlar
yalnız Codex'in salt-okunur teşhis/test kaydı içindir. Her maddede **hedef**,
**beklenen sonuç**, **gerçek sonuç**, **kanıt zamanı** ve **durum**
(`GEÇTİ`/`KALDI`/`BAŞARISIZ`/`ONAY BEKLİYOR`) yazılmalıdır.

### A. Hedef kimliği ve değişiklik öncesi güvenlik kapısı

1. Fiziksel cihazı model/seri numarasını rapora açık hassas değer yazmadan
   kullanıcıyla doğrula. `systemd-detect-virt` sonucunu kaydet; VM sonucu varsa
   fiziksel kabulü durdur.
2. Salt-okunur olarak `uname -a`, CachyOS release, `cat /proc/cmdline`,
   `findmnt -no SOURCE,FSTYPE,OPTIONS /`, `findmnt /boot/efi`,
   `findmnt --target /boot`, `lsblk -f`, `id localadm` ve GRUB dosya/araç
   varlığını kaydet.
3. Beklenen: UEFI, Btrfs, `/dev/...[/@]`, `/boot/efi` FAT32, `/boot` için ayrı
   dosya sistemi yok, GRUB, `localadm` wheel ve etkin yönetici hesabı. Herhangi
   bir uyuşmazlıkta dur; repartition, bootloader dönüşümü veya preflight bypass
   yapma.
4. İnternet erişimini HTTPS ile, boş alanı `df`/`btrfs filesystem usage` ile,
   AC durumunu gerçek güç kaynağından doğrula. Paketler, AUR çalışma alanı,
   Golden/Active ve snapshot testleri için yeterli alan yoksa dur.
5. Kullanıcıdan önyüklenebilir kurtarma USB'si ile harici geri yüklenebilir veri
   yedeğinin gerçekten hazır olduğunu doğrula. Bu iki madde salt komut çıktısı
   veya varsayımla geçmiş sayılamaz.
6. `btrfs device stats /` ve mevcut scrub durumunu kaydet. Sıfır olmayan hata
   sayacında veya tamamlanmamış/başarısız scrub durumunda boot zincirine dokunma.

### B. Repo ve değişiklik öncesi kalite tabanı

1. `git status --short`, remotes, branch, son commit ve `git pull --ff-only`
   sonucunu kaydet. Kullanıcı değişikliği varsa koru ve kapsamı ayır.
2. Tarih, kernel, CachyOS sürümü, hedef türü ve commit hash'iyle yeni QA raporu
   başlat.
3. Ruff check/format, bütün Python testleri, Bash syntax, ShellCheck,
   desktop-file validation, JSON/XML, systemd unit verify ve Qt offscreen smoke
   çalıştır. Başlangıçta hata varsa provisioning yapma; kök nedeni düzelt,
   diff'i incele ve bütün kapıyı yeniden geçir.
4. Gizli değer taraması yap; parola/token/hash/log/gerçek kullanıcı verisi
   repoda veya staged diffte olmamalıdır.

### C. Grafik preflight ve provisioning

1. Plasma/Dolphin'den `CachyOS-Kurulum-Uygulamasi.desktop` dosyasını aç.
   Başlatıcı terminal göstermemeli; gerekiyorsa yalnız PyQt6 bootstrap için
   standart PolicyKit penceresi görünmelidir.
2. **Sistem ön kontrolünü çalıştır** ve GUI sonucunu A bölümündeki gerçek
   bağlama sonuçlarıyla karşılaştır. Çelişkide dur ve kanıtı koru.
3. Kurtarma/yedek onayı ancak gerçekten hazırsa işaretlenir. Çalışan adı,
   görünen ad ve güçlü parola GUI alanlarına girilir; parola Codex çıktısına,
   komut argümanına, rapora veya ekran görüntüsüne girmez.
4. **Tam kurulumu başlat** ve paket/AUR, çalışan hesabı, Wine/MicroSIP, Deep
   Freeze, state alt birimi, initramfs, GRUB ve ilk Golden bitene kadar GUI
   ilerlemesini izle. Uygulamayı öldürme ve gücü kesme.
5. Beklenen ara durum: `phase=provisioned`, çalışan mevcut ve wheel/sudo dışı,
   Golden/Active hazır, transaction beklemiyor, GRUB parolası yok, THAWED bakım
   modu. Bu altı durumdan biri farklıysa finalize'a geçme.

### D. Finalize öncesi gerçek masaüstü kabulü

1. Önce `localadm`, sonra çalışan hesabında Chrome, Slack, AnyDesk,
   LibreOffice, Zoiper ve Wine/MicroSIP'i gerçek pencere olarak aç. Dosya,
   executable, desktop entry veya süreç varlığı tek başına geçmez.
2. Çalışan masaüstü kısayollarını, Breeze Dark görünümünü, interneti ve uygulama
   yeniden açılışlarını doğrula.
3. Gerçek mikrofon, hoparlör ve kulaklığı ayrı aygıtlar olarak seç. Giriş
   seviyesini, çıkış sesini ve aygıt geçişini doğrula; mümkünse MicroSIP/Zoiper
   gerçek test araması yap. Monitor/dummy/VirtualBox sanal kaynak fiziksel kabul
   değildir.
4. Çalışan hesabında `wheel`/`sudo` bulunmamalı ve parolasız sudo reddedilmeli.
   Genel ayrıcalıklı masaüstü işlemi `localadm` parolası istemeli; `localadm`
   yönetici işlemini başarıyla tamamlayabilmelidir.
5. Çalışan oturum açılışında QMK/VIA, ayrık GPU, NetworkManager bağlantı
   kontrolü ve pil threshold okuması gereksiz yönetici penceresi göstermemeli.
   Aynı zamanda listede olmayan genel `pkexec` işlemi parola istemelidir.
6. Ancak bütün D maddeleri gerçekten geçerse uygulamadaki üç kabul kutusunu
   işaretle. Bir hesabın veya fiziksel aygıtın testi eksikse finalize yasaktır.

### E. Finalize ve ilk FROZEN açılış

1. Güçlü GRUB bakım parolasını kullanıcı doğrudan uygulamanın iki gizli alanına
   girer. Codex parolayı sormaz, kopyalamaz, kaydetmez veya tekrar etmez.
2. **Kurulumu tamamla ve FROZEN yap** akışını çalıştır; ev şablonları, GRUB
   özeti, Golden yayını ve FROZEN planı tamamlanana kadar güç kesme.
3. Uygulamanın reboot teklifini kullan. İlk GRUB ekranında tek kurumsal girdi ve
   FROZEN başlığı görünmeli. FROZEN normal seçim parolasız açılmalıdır.
4. Ayrı bir bootta THAWED seçiminin `cachyadmin` doğrulaması istediğini, yanlış
   parolanın reddedildiğini ve parolanın ekranda görünmediğini doğrula.
5. İlk FROZEN boot sonrası `/proc/cmdline` içinde `cachy.freeze=1`, kök kaynakta
   `@active`, Golden/Active varlığı, initramfs içinde reset hook'u, boot-attempt
   sayacı, boot-health ve Dashboard FROZEN durumu kaydedilir.
6. `journalctl -b -p err`, CachyFreeze servisleri ve audit logları incelenir.
   Gerçek hata varsa davranış testine geçilmez.

### F. FROZEN, THAWED ve tek-sefer THAWED davranışı

1. FROZEN çalışan evinde benzersiz dosya ve görünür ayar değişikliği oluştur;
   uygulamadan reboot et ve ikisinin de kaybolduğunu doğrula.
2. FROZEN `localadm` yönetilen evinde zararsız, benzersiz test izi oluştur;
   reboot sonrası şablondan döndüğünü doğrula. Gerçek kullanıcı verisini test
   için kullanma.
3. GUI'den kalıcı THAWED planla. Boot sonrası `cachy.freeze=0`, kök `@` ve
   Dashboard THAWED olmalı. Dosya oluştur; iki reboot sonrasında kalıcı olduğunu
   doğrula.
4. GUI'den **yalnızca bir kez THAWED** planla. Sonraki boot THAWED, onu takip
   eden boot otomatik FROZEN olmalıdır; `cachy_once` başarılı THAWED grafik
   bootundan sonra temizlenmelidir.
5. Her bootta süre, GRUB başlığı, cmdline, kök alt birimi, Golden/Active,
   transaction, boot sayacı, boot-health ve audit olayını aynı rapor satırında
   kaydet.

### G. Snapshot bütünlük ve rollback kabulü

1. Snapshotlar sayfasından iki benzersiz açıklamalı snapshot oluştur; kontrollü
   dosya farkı ekle.
2. İkisinde metadata doğrulaması ve tam `btrfs send` SHA-256 doğrulaması yap;
   UUID, salt-okunur, checksum, boyut ve sağlık alanlarını kaydet.
3. Snapshotları karşılaştır; beklenen kontrollü yol görünmeli ve liste
   sınırlandırma/truncation durumu doğru raporlanmalıdır.
4. Bir snapshotı export et, manifest/stream boyutunu kaydet, yeniden import et
   ve import edilen yerel salt-okunur snapshotı tam doğrula.
5. Export'un yalnız bir test kopyasında kontrollü tek byte boz; import checksum
   hatasıyla reddedilmeli ve katalogda yarım nesne kalmamalıdır. Golden/Active
   veya gerçek snapshot alt birimini elle bozma.
6. Bir test snapshotını GUI'den sil ve katalog/Btrfs nesnesinin kalktığını
   doğrula. Sağlıklı snapshota rollback planla, uygulamadan reboot et ve hem
   içerik hem FROZEN modunu doğrula.

### H. Güncelleme ve kullanıcı yaşam döngüsü

1. GUI'den güncelleme kontrolü yap; sonuç ve ağ-politikası durumunu kaydet.
2. Yalnız THAWED modda korumalı güncelleme çalıştır. Güncelleme öncesi rollback
   snapshotı, pacman doğrulaması, uygulama yeniden testleri ve yeni Golden'ı
   doğrula. Güncelleme sırasında reboot/güç kesme yapma.
3. Geçici standart kullanıcıyı GUI'den oluştur; parola değiştir, kilitle/aç,
   autologin ayarla/kaldır, yedekleyerek sil ve yedekten geri yükle.
4. Her aşamada wheel/sudo reddini doğrula. Geri yükleme sırasında düz parola
   veya parola hash'i süreç argümanında görünmemeli; root-only yedek izinlerini
   kaydet.
5. Geçici kullanıcı ve yedeği temizlenmeden önce gereken kanıtı raporla; gerçek
   çalışan hesabını yaşam döngüsü testi için silme.

### I. Stres, performans ve uzun kullanım

1. Başlamadan sağlıklı Golden, doğrulanmış geri dönüş snapshotı, AC, yedek ve
   yeterli alanı yeniden doğrula. Başlangıç `btrfs filesystem usage`, device
   stats, scrub, RAM, süreç sayısı, uygulama RSS/PSS ve disk kullanımını kaydet.
2. Kontrollü küçük değişikliklerle 25 snapshot oluştur. Hepsinde metadata,
   ilk/orta/son dahil seçili örneklerde tam Btrfs doğrulaması çalıştır. Retention
   cleanup sonucunda beklenen sayı ve katalog tutarlılığını kanıtla.
3. Uzun tam doğrulama sürerken ikinci yazma işlemi başlat; işlem kilidi güvenli
   biçimde reddetmeli, ilk işlem ve katalog bozulmamalıdır.
4. FROZEN, kalıcı THAWED ve tek-sefer THAWED içeren 10 boot çevrimi yap. Her
   çevrimde süre, mod, cmdline, alt birim, boot sayacı, Btrfs ve journal hatası
   kaydet.
5. Uygulamayı aç/kapat ve en az 30 yenileme/sayfa geçişi yap. Başlangıç/bitiş
   RSS/PSS, sistem belleği ve süreç sayısını karşılaştır; zombie, asılı helper,
   kilit dosyası veya sürekli bellek büyümesi olmamalıdır.
6. Snapshot apparent/exclusive boyutları ile export gerçek disk tüketimini
   karşılaştır; test sonu Btrfs usage/device stats/scrub değerlerini başlangıçla
   kıyasla.
7. En az iki saat Chrome, Slack, MicroSIP/Zoiper ve yönetim uygulamasını birlikte
   kullan; otomatik snapshot timer'ının beklenen zamanda ve yalnız THAWED kökte
   çalıştığını doğrula.

### J. Yıkıcı test onay kapısı

Beklenmeyen güç kesintisi, zorla kapatma, boot başarısızlığı veya otomatik
rollback testi fiziksel laptopta kendiliğinden başlatılmaz. Önce sağlıklı Golden,
harici veri yedeği, kurtarma USB'si, AC güç, doğrulanmış geri dönüş snapshotı ve
kullanıcının o test için ayrıca açık onayı kaydedilir. İlk uygulama disposable
VM'de yapılır. Golden yayını, pacman, mkinitcpio veya GRUB yazımı sırasında asla
güç kesilmez; EFI/GRUB dosyaları fiziksel cihazda bilerek bozulmaz.

### K. Son kalite, rapor ve GitHub

1. B bölümündeki bütün statik/Python/GUI testlerini tekrar çalıştır. Ayrıca
   journal error, boot-health, Btrfs device stats ve scrub sonucunu kaydet.
2. Geçen, kalan, başarısız, uygulanamaz ve kullanıcı onayı bekleyen testleri
   ayrı başlıklarda yaz. Yapılmamış testi geçmiş gösterme; VM sonucunu fiziksel
   sonuçla birleştirme.
3. Kod değiştiyse yalnız ilgili dosyaları stage et; diff/secret kontrolü yap,
   kısa commit oluştur ve güncel kullanıcı tercihi değişmediyse doğrudan
   `main` dalına push et.
4. GitHub Actions tamamen yeşil olana kadar izle. Koşu URL'si, commit hash'i,
   tarih, kernel ve hedef türünü QA raporuna ekle.

## Kesin güvenlik kuralları

- `btrfs check --repair` çalıştırma.
- `@`, `@golden`, `@active` veya state/snapshot alt birimlerini elle silme.
- Desteklenmeyen boot/disk düzeninde ön kontrolü atlatma.
- Golden yayını, pacman, mkinitcpio veya GRUB yazımı sırasında kapatma yapma.
- Parola, token, gerçek çalışan verisi, cihaz UUID'si veya SSH anahtarı commit
  etme.
- Fiziksel cihazda yıkıcı boot/elektrik testini varsayma; koşullar sağlanmadan
  ve kullanıcı açıkça onaylamadan başlatma.
- Hata anında önce log, journal, `findmnt`, Btrfs alt birim listesi ve uygulama
  durumunu koru; kanıt toplamadan sistemi değiştirme.
