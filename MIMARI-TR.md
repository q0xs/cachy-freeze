# CachyOS Workstation Management Platform Mimarisi

Bu belge, grafik yönetim uygulamasının güven sınırlarını, Btrfs veri modelini ve
kesinti kurtarma davranışını tanımlar. Günlük yönetim işlemleri **Cachy Freeze
Yönetim Merkezi** üzerinden yapılır; normal kullanıcı terminal kullanmaz.

## Bileşenler

- `app/cachy_freeze_gui`: PyQt6 yönetim arayüzü. Ayrıcalıksız çalışır.
- `CachyOS-Kurulum-Uygulamasi.desktop` ve `app/cachy-freeze-setup`: Temiz
  CachyOS üzerinde terminal göstermeden aynı GUI'yi Kurulum sayfasında açan,
  eksikse yalnızca PyQt6 çalışma zamanını PolicyKit ile hazırlayan bootstrap.
- `app/cachy-freeze-manager-helper`: PolicyKit tarafından yalnızca izin verilen
  işlemleri ve doğrulanmış argümanları root backend'e ileten dar güven sınırı;
  ön kontrol, hazırlama ve kurulum tamamlama eylemleri de aynı allow-list'tedir.
- `src/cachy_freeze`: Snapshot, freeze, boot, kullanıcı, ayar, güncelleme,
  metadata, audit ve transaction katmanları.
- `deepfreeze/initcpio`: Kök bağlanmadan önce Active'i Golden'dan yeniden
  oluşturan ve yarım kalmış rotasyonları kurtaran initramfs servisi.
- `deepfreeze/systemd`: Kalıcı state, başarılı boot onayı ve otomatik snapshot
  zamanlayıcısı.

GUI hiçbir shell komutu oluşturmaz. Ayrıcalıklı süreçler argüman dizileriyle
çalıştırılır; parola yalnızca kapalı standart giriş kanalı üzerinden taşınır ve
komut satırına, JSON yanıtına veya audit loguna girmez.

İlk kurulumda GUI mevcut doğrulanmış installer zincirini yeniden kullanır.
Çalışan ve GRUB parolaları helper'a stdin üzerinden gelir; helper bunları yine
stdin üzerinden etkileşimsiz installer kipine aktarır. Kurulum çıktısı GUI'de
canlı gösterilir ve `/var/log/cachyos-workstation-install.log` içinde tutulur.
Kurulumla birlikte `installer`, `deepfreeze`, `user`, `policies` ve `vendor`
payload'ları `/usr/lib/cachy-freeze/deployment` altına kopyalanır; böylece aynı
Kurulum sayfası yeniden açıldığında yarım kalan durum belirlenebilir ve ikinci
aşama repo klasörüne bağlı kalmadan tamamlanabilir.

## Btrfs alt birim düzeni

| Alt birim | Görev |
| --- | --- |
| `@` | THAWED bakım kökü |
| `@golden` | Salt-okunur, yayınlanmış sağlam kaynak |
| `@active` | Bir Frozen boot için yazılabilir çalışma kökü |
| `@golden.previous`, `@active.previous` | Son geri dönüş çifti |
| `*.next`, `*.previous.pending` | Kesintiye dayanıklı transaction adları |
| `@golden.failed` | Otomatik rollback sonrası tanı için korunan hatalı Golden |
| `@cachy-snapshots` | Kullanıcı ve otomatik snapshot geçmişi |
| `@cachy-state` | Root rollback'ten bağımsız metadata, ayar ve boot sağlığı |

Snapshot katalog yazımları geçici dosya, `fsync`, atomik `replace` ve dizin
`fsync` sırasını kullanır. Golden/Active yayını kalıcı transaction günlüğüyle
`preparing`, `prepared`, `golden-committed` ve `active-committed` evrelerinden
geçer. Her adımın alt birim adı, güç kesintisinden sonra ileri tamamlama veya
güvenli geri dönüş için yeterlidir.

## Boot ve otomatik kurtarma

Frozen boot sırasında initramfs şu sırayı uygular:

1. Üst seviye Btrfs ağacını bağlar.
2. Yarım kalmış Golden ve Active rotasyonlarını adlarından kurtarır.
3. Kalıcı boot deneme sayacını artırır.
4. Ayarlanan sınır aşılmış ve önceki sağlam Golden varsa hatalı Golden'ı
   `@golden.failed` olarak koruyup önceki Golden'ı otomatik geri yükler.
5. Yeni yazılabilir Active'i doğrulanmış salt-okunur Golden'dan oluşturur.

Grafik hedefe ulaşan `cachy-freeze-boot-health.service` sayacı sıfırlar ve audit
kaydını yazar. Böylece elektrik kesintisi veya erken boot çökmesi olumlu sağlık
onayı sayılmaz. Önceki Golden bulunmaması halinde sistem mevcut Golden'ı silmez;
uyarı state içinde korunur.

Kalıcı FROZEN, kalıcı THAWED ve yalnızca bir sonraki açılış için THAWED modları
desteklenir. Tek seferlik seçim, THAWED grafik hedefi başarıyla ulaştıktan sonra
boot sağlık servisi tarafından GRUB environment içinden doğrulanarak temizlenir.

## Snapshot sözleşmesi

Her snapshot; kimlik, Btrfs UUID/parent UUID, UTC tarih-saat, kernel, görünen ve
özel boyut, açıklama, oluşturan kullanıcı, Frozen/bootable bilgisi, metadata
SHA-256, rollback sayısı, oluşturma süresi, sağlık ve kaynak alanlarını içerir.
Doğrulama UUID, salt-okunur özelliği ve metadata checksumunu; tam doğrulama
ayrıca `btrfs send` akış SHA-256 değerini hesaplar.

Export, Btrfs send akışını ve root erişimli JSON manifestini birlikte üretir.
Import önce manifest ve akış checksumunu doğrular, tek bir alt birim kabul eder
ve alınan salt-okunur nesneden yerel salt-okunur snapshot oluşturur.

## Yönetim arayüzü

Arayüz Dashboard, Snapshotlar, Kullanıcılar, Güncellemeler, Audit Logları ve
Ayarlar sayfalarından oluşur. Dark/light tema, disk ve boot sağlığı, uyarılar,
snapshot geçmişi/karşılaştırma/export/import/rollback, standart hesap
oluşturma-silme-kilitleme-parola-otomatik giriş, güncelleme kontrolü ve politika
ayarları GUI içinden yönetilir.

`localadm` korumalı yönetici hesabıdır. Yeni hesaplar wheel ve sudo gruplarına
eklenmez. Kullanıcı silinmeden önce kimlik bilgisi ve ev dizini root erişimli
bir geri yükleme yedeğine alınır. PolicyKit yükseltmesi yalnızca yönetim
uygulamasının izin listeli yardımcısı için geçerlidir.

## Güncelleme ve MicroSIP güvenliği

Sistem güncellemesi yalnızca THAWED kökte çalışır; önce geri dönüş snapshotı
oluşturur, pacman veritabanını doğrular ve başarılı sonuçta yeni Golden
yayınlar. Otomatik snapshot servisi Frozen kökte değişiklik yapmadan çıkar.

MicroSIP resmi HTTPS sayfasından retry ve süre sınırlarıyla atomik indirilir.
ZIP CRC ve yol geçişi, tek kök `MicroSIP.exe`, PE biçimi, arşiv/exe SHA-256 ve
Wine üzerinden izole ekran smoke testi doğrulanmadan kurulum başarılı sayılmaz.

## Doğrulama kapsamı

- Ruff, Python birim testleri, Bash sözdizimi, ShellCheck, XML/JSON ve systemd
  unit doğrulaması.
- Gerçek Btrfs loop aygıtında snapshot, checksum, compare, export/import,
  rollback, retention ve 25 ardışık snapshot stres döngüsü.
- Golden/Active kesinti noktaları ve art arda başarısız boot otomatik rollback.
- Gerçek Linux hesabında oluşturma, kilitleme, otomatik giriş, yedekli silme,
  geri yükleme ve root yetkisi reddi.
- İki gerçek CachyOS kerneliyle mkinitcpio üretimi ve `lsinitcpio` içerik testi.
- Qt offscreen arayüz smoke testi.

Loop aygıt ve initramfs testleri CachyOS sanal makinesinde güvenle çalışır.
EFI firmware ve gerçek GRUB reboot zincirinin son kabul testi, UEFI olarak
açılmış yedekli pilot cihazda yapılmalıdır; BIOS ile açılmış canlı VM sonucu
UEFI fiziksel kabul testi olarak değerlendirilmez.
