# Codex CLI devam talimatı

Bu dosya, fiziksel CachyOS laptopta yapılacak canlı kabul ve stres testinin
tek başlangıç kaynağıdır. Önce bu dosyanın tamamını, ardından `MIMARI-TR.md`,
`KURULUM-TR.md` ve `PILOT-NOTLARI.md` dosyalarını oku. Mevcut mimariyi analiz
etmeden kod değiştirme.

## Doğrulanmış durum — 1 Ağustos 2026

Windows host üzerinde yalnızca projeye ayrılmış
`CachyFreeze-QA-20260801` VirtualBox sanal makinesi kullanıldı. Kullanıcının
önceden var olan sanal makinelerine ve host disk düzenine dokunulmadı.

Doğrulanan VM düzeni:

- CachyOS 7.1.3-2-cachyos, Plasma 6.7, UEFI64;
- 80 GiB sanal disk, GPT, 1 GiB FAT32 EFI ve kalan alan Btrfs;
- kök `@` alt birimi, `/boot` Btrfs kök içinde, `/boot/efi` ayrı EFI bölümü;
- GRUB normal EFI girdisi ve geri dönüş `EFI/BOOT/BOOTX64.EFI` dosyası;
- `NetworkManager`, `sshd`, `sddm` ve `vboxservice` aktif;
- temiz kurulum ISO SHA-256 değeri CachyOS resmî yayın değeriyle eşleşti.

Birleşik masaüstü kurulum uygulaması gerçek Plasma Wayland oturumunda açıldı.
PolicyKit parola penceresi görüntülendi ve `localadm` ile yetkilendirme
doğrulandı. Uygulamanın ön kontrolü gerçek sistemde şu sonucu verdi:

- firmware: UEFI;
- filesystem: Btrfs;
- current subvolume: `@`;
- root device: `/dev/sda2`;
- ayrı `/boot` yok ve `/boot/efi` bağlı.

İlk hazırlama aşaması gerçek paket indirmeleri ve AUR derlemeleriyle tamamlandı.
Son durum `phase=provisioned`, Golden mevcut, GRUB parolası henüz ayarlanmamış,
sonraki mod THAWED ve bekleyen Btrfs işlemi yoktur. Bilerek yapılmayanlar:

- GUI canlı uygulama/ses/yönetici kabul kutuları onaylanmadı;
- `setup-finalize` çalıştırılmadı;
- GRUB bakım parolası oluşturulmadı;
- FROZEN yeniden başlatma, rollback, elektrik kesintisi ve stres testleri
  başlatılmadı.

VM güvenli biçimde kapalıdır. Yerel geri dönüş noktası:

- snapshot: `03-provisioned-powered-off`;
- snapshot UUID: `84dfc083-47f0-4688-87eb-d76f9ddbe36a`.

Bu VirtualBox durumu yalnızca yerel Windows test ortamındadır. Fiziksel laptopta
repo klonundan başlayacaksan VM durumunu fiziksel sisteme taşınmış varsayma.

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
