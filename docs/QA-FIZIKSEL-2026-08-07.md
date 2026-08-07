# Fiziksel CachyOS Pilot QA — 7 Ağustos 2026

## Kapsam ve kimlik

- Hedef: fiziksel CachyOS pilot laptop olduğu henüz kullanıcı tarafından
  doğrulanmadı; yürütme ortamı `container-other` bildirdi.
- İşletim sistemi: CachyOS Linux (sürüm alanı sistem dosyasında yayımlanmamış).
- Kernel: `7.1.6-1-cachyos`.
- Repo commit: `106b304` (`main`, `origin/main` ile güncel).
- Sonuç: **GÜVENLİK/KOD KAPISI TAM GEÇMEDİ — PROVISIONING YAPILMADI**.

Bu raporda cihaz UUID'si, seri numarası, parola/parola hash'i, gerçek çalışan
kimliği ve hassas log bulunmaz.

## Geçen kontroller

- Repo temiz klonlandı; remote ve son commitler incelendi.
- `git pull --ff-only`: güncel.
- UEFI firmware görünür.
- Kök Btrfs ve kök alt birimi `@`.
- EFI dosya sistemi `/boot/efi` üzerinde bağlı.
- Ayrı `/boot` dosya sistemi yok; `/boot`, Btrfs kök içindedir.
- GRUB aracı mevcut.
- `localadm`, `wheel` üyesi.
- AC güç bağlı.
- Kök dosya sisteminde yaklaşık 228 GiB boş alan var.
- Btrfs device error sayaçları sıfır.
- Btrfs scrub durumu hata bildirmedi.
- Ruff check geçti.
- Ruff format check geçti (25 dosya).
- Python birim testleri geçti (33/33).
- Bash sözdizimi geçti.
- Desktop-file doğrulaması hata vermedi (bir kategori ipucu var).
- JSON ve XML doğrulaması geçti.
- PolicyKit çalışan kuralı semantik testi geçti.
- Qt/PyQt offscreen GUI smoke testi geçti.

## Kalan / doğrulanması gereken kontroller

- Kullanıcı, hedefin gerçekten yedekli fiziksel pilot laptop olduğunu
  doğrulamalı.
- Önyüklenebilir CachyOS kurtarma USB'sinin hazır olduğu doğrulanmalı.
- Harici, geri yüklenebilir önemli veri yedeği doğrulanmalı.
- `localadm` hesabının etkin parola durumu ayrıcalıklı salt-okunur kanıtla
  doğrulanmalı.
- HTTPS internet erişimi sandbox dışındaki gerçek sistem bağlamında
  doğrulanmalı.
- ShellCheck severity=error çalıştırılmalı; araç mevcut değil.
- `systemd-analyze verify` sandbox dışında tam çalıştırılmalı; mevcut çalışmada
  yalnız sandbox izin uyarısı alınarak kısmi doğrulama yapıldı.
- Grafik uygulamanın gerçek Plasma/Dolphin başlatması ve grafik preflight henüz
  yapılmadı.

## Başarısız / engelleyici durumlar

- Fiziksel hedef kimliği otomatik olarak kesinleştirilemedi:
  `systemd-detect-virt` yürütme ortamını `container-other` bildirdi.
- Değişiklik öncesi kod kapısı ShellCheck ve tam systemd verify eksikleri
  nedeniyle bütünüyle geçmedi.

## Uygulanmayan adımlar

Provisioning, finalize, reboot, FROZEN/THAWED, snapshot, güncelleme, kullanıcı
yaşam döngüsü, stres, uzun kullanım ve yıkıcı testlerin hiçbiri başlatılmadı.
Kapıların tamamı gerçekten geçmeden bu adımlar geçmiş sayılmayacaktır.

## Onay bekleyen

Fiziksel güç kesintisi, zorla kapatma veya boot rollback testi için ayrıca açık
kullanıcı onayı gerekir. Bu aşamaya henüz gelinmedi.

## Kullanıcının güncel kararı ve devir notu

Kullanıcı 7 Ağustos 2026 tarihinde cihazın yeni kurulmuş olduğunu, cihazda
korunması gereken veri bulunmadığını ve arıza halinde yeniden formatlamayı kabul
ettiğini belirterek kurtarma USB'si ve harici yedek olmadan ilerlenmesini istedi.
Repo güvenlik sözleşmesi bu iki koşulun atlanmasına izin vermediği için fiziksel
provisioning yine başlatılmadı. Daha sonraki bir Codex oturumu bu tercihi
güvenlik kapısının geçtiği şeklinde yorumlamamalıdır.

Kullanıcı sohbet içinde bir yönetici parolası paylaştı. Parola kullanılmadı,
kaydedilmedi ve bu rapora dahil edilmedi. Paylaşıldığı için değiştirilmesi
gereken açığa çıkmış bir parola olarak değerlendirilmelidir. Ayrıcalıklı grafik
işlemlerde kullanıcı parolayı doğrudan PolicyKit gizli alanına girmelidir.

Güvenli devam noktası:

1. Kurtarma USB'si ve geri yüklenebilir harici yedeği gerçekten hazırla.
2. Paylaşılmış yönetici parolasını değiştir.
3. Eksik ShellCheck ve tam systemd unit verify kapısını geçir.
4. Plasma/Dolphin içinden masaüstü başlatıcısını aç ve grafik preflight yap.
5. Ancak bütün fiziksel kapı maddeleri geçerse grafik provisioning'e başla.
