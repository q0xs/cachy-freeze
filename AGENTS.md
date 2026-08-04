# Codex çalışma kuralları

Bu dosya bütün repo için geçerlidir. Alt dizindeki daha özel `AGENTS.md`
dosyası kendi kapsamındaki ek kuralları tanımlar.

## Başlangıç ve bağlam

- Önce bu dosyanın tamamını; sonra `CODEX-CLI-DEVAM-TALIMATI.md`, `README.md`,
  `MIMARI-TR.md`, `KURULUM-TR.md`, `GITHUB-ILE-CALISMA.md` ve
  `PILOT-NOTLARI.md` dosyalarını oku.
- Fiziksel laptop görevi verildiyse ayrıca
  `CODEX-CLI-FIZIKSEL-GOREV-METNI.md` içindeki uçtan uca kabul sözleşmesini oku.
- Her turda `git status --short`, `git remote -v` ve son commitleri incele.
  Kullanıcı değişikliklerini silme, stash etme, restore etme veya ezme.
- Windows host, VirtualBox VM ve fiziksel CachyOS laptopu ayrı hedefler olarak
  tut. Snapshot, UUID, boot modu veya test sonucunu hedefler arasında taşıma.
- Devam belgesindeki checkpoint yalnız devir notudur. Gerçek hedefin UEFI,
  Btrfs, GRUB, kullanıcı, Golden/Active ve mod durumunu yeniden doğrula.

## Kullanıcı arayüzü sınırı

- Normal kullanıcı kurulumu yalnız `CachyOS-Kurulum-Uygulamasi.desktop` ve
  uygulamanın **Kurulum** sayfasından yapılır.
- Kullanıcıya numaralı `.sh`, `sudo`, terminal kurulum veya bakım akışı sunma.
- Terminal yalnız Codex'in repo işlemleri, geliştirme, test, log ve salt-okunur
  teşhisi içindir.
- Canlı kabulte yalnız dosya/komut varlığını yeterli sayma; gerçek uygulama
  penceresini ve gerçek donanım davranışını doğrula.

## Güvenlik

- Parola, token, SSH anahtarı, cihaz UUID'si, gerçek kullanıcı verisi veya gizli
  değeri çıktı, komut argümanı, log, ekran görüntüsü, rapor ya da repoya koyma.
- Parola ve yeniden kullanılabilir parola hash'leri mevcut stdin gizli veri
  kanalıyla taşınmalıdır; süreç argümanına eklenemez.
- Desteklenmeyen UEFI/Btrfs/`@`/GRUB/EFI düzeninde dur. Preflight'i atlatma veya
  sistemi zorla dönüştürme.
- `btrfs check --repair` çalıştırma. Gerçek `@`, `@golden`, `@active`, state veya
  snapshot alt birimlerini elle bozma/silme.
- Golden yayını, pacman, mkinitcpio veya GRUB yazımı sırasında güç kesme.
- Fiziksel cihazda yıkıcı boot/güç testi için sağlıklı Golden, harici yedek,
  kurtarma USB'si, AC güç, geri dönüş snapshotı ve ayrıca açık kullanıcı onayı
  gerekir.

## Kod ve test kapısı

- Shell komutlarını Python veya GUI içinde string birleştirme ya da `shell=True`
  ile çalıştırma; doğrulanmış argüman dizileri kullan.
- Bütün yazma işlemlerini mevcut işlem kilidi, atomik yazma ve transaction
  sözleşmeleriyle uyumlu tut.
- Değişiklikten önce ve sonra en az Ruff check/format, tüm Python birim testleri,
  Bash syntax, ShellCheck, systemd verify, desktop-file validation ve Qt
  offscreen smoke çalıştır.
- Btrfs, initramfs ve GRUB entegrasyon testlerini disposable VM veya açıkça
  ayrılmış pilot dışında çalıştırma.
- Yapılmamış, uygulanamaz veya kullanıcı onayı bekleyen testi geçmiş gösterme.
  VM ses aygıtını fiziksel mikrofon/kulaklık kabulü sayma.

## Git ve GitHub

- Yalnız ilgili dosyaları adlarıyla stage et. `git diff --check`, staged diff ve
  çalışma ağacını committen önce incele.
- Kısa, amaç odaklı commit oluştur. Güncel kullanıcı tercihi değişmedikçe PR
  açmadan doğrudan `main` dalına push et; force-push kullanma.
- GitHub Actions tamamen yeşil olana kadar izle. Hata varsa logdaki kök nedeni
  düzelt, testleri tekrarla ve yeni commit gönder.
- Gerçek QA sonucunu tarih, hedef, kernel ve commit ile raporla; parolaları ve
  hassas kimlikleri rapora yazma.
