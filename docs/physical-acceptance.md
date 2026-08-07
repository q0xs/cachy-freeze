# Physical CachyOS Acceptance Plan

Aşağıdaki metnin tamamını Codex CLI'ye görev olarak ver:

---

Repo: https://github.com/q0xs/cachy-freeze

Fiziksel, yedekli CachyOS pilot laptop üzerinde sıfırdan güvenlik doğrulaması,
grafik kurulum, canlı kabul, FROZEN/THAWED, snapshot, güncelleme, kullanıcı,
stres ve son kalite testlerini tamamla. Repo içindeki `AGENTS.md` kurallarına ve
alt dizinlerdeki daha özel `AGENTS.md` dosyalarına eksiksiz uy.

ÖNEMLİ HEDEF AYRIMI:

- Eski veya güncel VirtualBox VM, snapshot adı/UUID'si, Golden/Active, kullanıcı
  veya test sonucu fiziksel laptopun durumu değildir.
- Önceki VM'de provisioning yapılmış olması fiziksel laptopta kurulum yapıldığı
  anlamına gelmez.
- Fiziksel hedefte her şeyi yeniden salt-okunur doğrula. VM sonucunu fiziksel
  kabul olarak raporlama.
- Repo checkpoint bilgisi yalnız devir notudur; `origin/main` HEAD, çalışma ağacı
  ve gerçek sistem durumu her başlangıçta yeniden kontrol edilmelidir.

1. REPO VE TALİMATLAR

- Repo yoksa güvenli biçimde klonla. Varsa önce `git status --short`,
  `git remote -v`, `git log -3 --oneline` çalıştır ve kullanıcı değişikliklerini
  koru. Temiz ve uyumluysa yalnız `git pull --ff-only` kullan.
- Sırasıyla kök `AGENTS.md`, `CODEX-CLI-DEVAM-TALIMATI.md`, `README.md`,
  `docs/architecture.md`, `docs/installation.md`, `docs/development.md` ve
  `docs/pilot-checklist.md` dosyalarının tamamını oku. İlgili alt dizindeki
  `AGENTS.md` dosyasını kod değiştirmeden önce ayrıca oku.
- Token, parola, SSH anahtarı, cihaz UUID'si, gerçek kullanıcı verisi, parola
  hash'i veya hassas logu çıktıya/repoya koyma.

2. NORMAL KULLANICI İÇİN YALNIZ GRAFİK AKIŞ

- Kullanıcıya `.sh`, `sudo` veya terminal kurulum talimatı verme.
- Normal kurulum yalnız Plasma/Dolphin içinden
  `CachyOS-Kurulum-Uygulamasi.desktop` ve uygulamanın Kurulum sayfasıyla yapılır.
- Terminali yalnız Codex repo işlemleri, geliştirme, test, log ve salt-okunur
  teşhis için kullan.
- Parolaları terminal argümanına, loga, rapora, ekran görüntüsüne veya dosyaya
  yazma. GUI gizli alanlarını ve mevcut stdin secret kanalını kullan.

3. FİZİKSEL GÜVENLİK KAPISI

Sistem değişikliğinden önce şunların tamamını doğrula ve yeni tarihli QA
raporuna hedef türü, kernel, CachyOS sürümü ve commit hash'iyle yaz:

- hedef fiziksel, yedekli pilot laptop;
- UEFI boot;
- kök Btrfs ve kök alt birimi `@`;
- EFI bölümü `/boot/efi` konumunda;
- ayrı `/boot` dosya sistemi yok;
- bootloader GRUB;
- `localadm` etkin parolalı ve wheel üyesi;
- internet, AC güç ve yeterli disk alanı;
- önyüklenebilir CachyOS kurtarma USB'si;
- harici, geri yüklenebilir önemli veri yedeği;
- başlangıç Btrfs device stats ve scrub sağlıklı.

Salt-okunur kanıt için gerekirse `uname -a`, CachyOS release,
`cat /proc/cmdline`, `findmnt`, `lsblk -f`, `id localadm`, `df`,
`btrfs filesystem usage /`, `btrfs device stats /` ve scrub status kullan.
Desteklenmeyen disk/boot düzeninde dur; preflight atlatma, repartition veya
zorla bootloader dönüşümü yapma.

4. DEĞİŞİKLİK ÖNCESİ KOD KAPISI

Provisioning veya boot değişikliğinden önce şunları çalıştır:

- Ruff check;
- Ruff format check;
- bütün Python birim testleri;
- Bash syntax;
- ShellCheck severity=error;
- desktop-file validation;
- JSON/XML doğrulama;
- systemd unit verify;
- Qt/PyQt offscreen GUI smoke;
- PolicyKit çalışan kuralı semantik testi.

Hata varsa kurulumdan önce kök nedenini belirle, güvenli düzeltmeyi yap, diff'i
incele ve bütün kapıyı yeniden çalıştır. Yapılmamış testi geçmiş gösterme.

5. GRAFİK PREFLIGHT VE PROVISIONING

- Dolphin'den masaüstü başlatıcısını aç. Terminal penceresi görünmemeli.
- Kurulum sayfasında **Sistem ön kontrolünü çalıştır**; sonucu gerçek
  UEFI/Btrfs/`@`/EFI/GRUB bağlama kanıtıyla karşılaştır.
- Kurtarma/yedek kutusunu yalnız gerçekten hazırsa işaretle.
- Standart çalışan kullanıcı adı/görünen adı ve güçlü parolayı GUI alanlarına
  gir. **Tam kurulumu başlat** akışını kullan.
- Paketler, AUR derlemeleri, çalışan hesabı, Wine/MicroSIP, CachyFreeze, state
  alt birimi, initramfs, GRUB ve ilk Golden tamamlanana kadar izle. Pacman,
  Golden, mkinitcpio veya GRUB yazımı sırasında kapatma/reboot yapma.
- Beklenen ara durum: `phase=provisioned`, çalışan wheel/sudo dışı,
  Golden/Active hazır, transaction yok, GRUB bakım parolası henüz yok ve sistem
  THAWED. Biri farklıysa finalize'a geçme.

6. FINALIZE ÖNCESİ CANLI KABUL

Önce `localadm`, sonra çalışan hesabıyla gerçek masaüstünde:

- Google Chrome, Slack, AnyDesk, LibreOffice, Zoiper ve Wine/MicroSIP'in gerçek
  pencerelerini aç. Yalnız executable veya desktop dosyası varlığını geçme.
- İnternet, masaüstü kısayolları ve Breeze Dark görünümünü doğrula.
- Gerçek mikrofon, hoparlör ve kulaklığı ayrı ayrı seç ve test et; mümkünse
  gerçek MicroSIP/Zoiper test araması yap. Dummy/monitor/VM aygıtını fiziksel
  test sayma.
- Çalışanın wheel/sudo dışında olduğunu ve parolasız sudo'nun reddedildiğini
  doğrula.
- Genel ayrıcalıklı bir masaüstü işleminin `localadm` parolası istediğini ve
  `localadm` hesabının işlemi yapabildiğini doğrula.
- Çalışan logininde QMK/VIA, ayrık GPU, NetworkManager bağlantı kontrolü veya pil
  threshold okuması için gereksiz yönetici penceresi çıkmamalı. Fakat listede
  olmayan genel `pkexec` işlemi `localadm` istemeli.

Bütün maddeler gerçekten geçmeden üç kabul kutusunu işaretleme, GRUB parolası
alma veya finalize başlatma.

7. FINALIZE VE İLK FROZEN BOOT

- Kullanıcının seçtiği güçlü GRUB bakım parolasını kullanıcı doğrudan GUI'nin
  iki gizli alanına girsin; parolayı isteme, kopyalama veya kaydetme.
- **Kurulumu tamamla ve FROZEN yap** akışını ve uygulamanın reboot teklifini
  kullan.
- GRUB'da tek kurumsal FROZEN girdisini ve FROZEN'ın parolasız açıldığını
  doğrula. Ayrı testte THAWED seçiminin `cachyadmin` parolası istediğini ve yanlış
  parolayı reddettiğini doğrula.
- İlk FROZEN bootta cmdline `cachy.freeze=1`, kök `@active`, Golden/Active,
  initramfs reset hook'u, boot sayacı, boot-health, journal ve Dashboard
  durumunu kaydet.

8. FROZEN/THAWED DAVRANIŞI

- FROZEN çalışan evinde benzersiz dosya ve ayar oluştur; GUI'den reboot sonrası
  kaybolduğunu doğrula.
- FROZEN `localadm` yönetilen evinde zararsız test izi oluştur; reboot sonrası
  şablondan döndüğünü doğrula.
- GUI'den kalıcı THAWED planla; cmdline `cachy.freeze=0`, kök `@` olmalı. Dosya
  oluştur ve iki rebootta kalıcı olduğunu doğrula.
- Tek-sefer THAWED planla; sonraki boot THAWED, takip eden boot otomatik FROZEN
  olmalı ve `cachy_once` temizlenmeli.
- Her bootta süre, GRUB başlığı, cmdline, alt birim, Golden/Active, transaction,
  boot sayacı, health ve audit olaylarını kaydet.

9. SNAPSHOT TESTLERİ

- GUI'den iki açıklamalı snapshot oluştur ve kontrollü dosya farkı ekle.
- İkisini metadata ve tam Btrfs send SHA-256 doğrulamasından geçir.
- Karşılaştırmada beklenen yolu gör.
- Export et, manifest/streami kaydet, import et ve tam doğrula.
- Yalnız export kopyasında tek byte boz; checksum reddini ve yarım katalog
  nesnesi kalmadığını doğrula. Golden/Active veya gerçek snapshotı elle bozma.
- Bir test snapshotını GUI'den sil.
- Sağlıklı snapshota rollback planla; uygulamadan reboot et ve içerik/modu
  doğrula.

10. GÜNCELLEME VE KULLANICI TESTLERİ

- GUI'den update check yap.
- Yalnız THAWED modda korumalı update uygula. Öncesi rollback snapshotı,
  pacman doğrulaması, uygulama yeniden testleri ve yeni Golden'ı kanıtla.
- Geçici standart kullanıcıyı GUI'den oluştur; parola değiştir, kilitle/aç,
  autologin ayarla/kaldır, yedekleyerek sil ve yedekten geri yükle.
- Her aşamada wheel/sudo reddini doğrula. Düz parola veya geri yüklenebilir hash
  süreç argümanına çıkmamalı; hash `chpasswd --encrypted` stdin kanalında kalmalı.

11. STRES VE PERFORMANS

Sağlıklı Golden, doğrulanmış rollback snapshotı, AC, yedek ve yeterli alan
olmadan başlatma:

- Kontrollü değişikliklerle 25 snapshot; hepsinde metadata, seçili ilk/orta/son
  örneklerde tam doğrulama ve retention cleanup.
- Uzun doğrulama sırasında ikinci yazma; işlem kilidi güvenli reddetmeli.
- FROZEN, THAWED ve tek-sefer THAWED içeren 10 boot çevrimi; her bootta süre,
  mod, sayaç, Btrfs ve journal.
- En az 30 GUI yenileme/sayfa geçişi; başlangıç/bitiş RSS, PSS, sistem belleği,
  süreç sayısı, zombie/asılı helper ve sürekli büyüme kontrolü.
- Test öncesi/sonrası Btrfs usage, device stats, scrub, snapshot apparent/
  exclusive boyutları ve export disk tüketimi.
- En az iki saat Chrome, Slack, MicroSIP/Zoiper ve yönetim uygulaması birlikte;
  otomatik snapshot timer doğrulaması.

12. YIKICI TEST ONAY KAPISI

Beklenmeyen güç kesintisi, zorla kapatma veya boot rollback testini fiziksel
laptopta kendiliğinden başlatma. Önce sağlıklı Golden, harici yedek, kurtarma
USB'si, AC güç, geri dönüş snapshotı ve benim o test için ayrıca açık onayım
bulunmalıdır. İlk test disposable VM'de yapılmalıdır. Golden yayını, pacman,
mkinitcpio veya GRUB yazımı sırasında güç kesme. Fiziksel EFI/GRUB dosyasını
bilerek bozma. `btrfs check --repair` çalıştırma.

13. SON KALİTE VE GITHUB

- Bütün statik/Python/GUI testlerini tekrar çalıştır; journal error,
  boot-health, Btrfs device stats ve scrub sonucunu kaydet.
- QA raporunda geçen, kalan, başarısız, uygulanamaz ve kullanıcı onayı bekleyen
  testleri ayrı yaz. Yapılmamış testi geçmiş gösterme.
- Kod değiştiyse yalnız ilgili dosyaları stage et, staged diff/secret kontrolü
  yap, kısa commit oluştur ve en son tercihim değişmediyse PR açmadan doğrudan
  `main` dalına push et.
- GitHub Actions tamamen yeşil olana kadar izle; başarısızsa logdaki kök nedeni
  düzelt ve yeniden çalıştır.
- Son rapora hedef türü, tarih, kernel, CachyOS sürümü, commit hash'i ve Actions
  URL'sini ekle; hiçbir parola veya hassas kimliği ekleme.

Şimdi repo ve fiziksel güvenlik kapısından başla. Güvenlik kapısı ve başlangıç
testleri tamamen geçmeden grafik provisioning yapma. Benden ayrıca açık onay
gerektiren yıkıcı teste gelince dur ve onay iste.

---
