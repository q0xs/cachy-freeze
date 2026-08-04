# Btrfs, initramfs ve GRUB kuralları

Bu dosya `deepfreeze/` altındaki bütün değişikliklere ek olarak kök `AGENTS.md`
kurallarını uygular.

- Btrfs alt birim adları, transaction evreleri ve initramfs kurtarma adımları
  kalıcı veri sözleşmesidir. Bir adı veya sırayı değiştirirken ileri kurtarma,
  önceki sürüm uyumluluğu ve güç kesintisi noktalarını birlikte test et.
- Mutasyon yalnız işlem kilidi ve üst-seviye Btrfs bağlaması içinde yapılmalıdır.
  Bağlı aygıt UUID'sini ve hedef alt birimi doğrulamadan silme/rename/snapshot
  çalıştırma.
- Golden salt-okunur kalmalı; Active Golden'dan üretilmelidir. Gerçek Golden,
  Active veya state alt birimini manuel test hedefi olarak kullanma.
- Initramfs hook'u `filesystems` öncesinde bulunmalı; üretilen her desteklenen
  initramfs içinde reset programını `lsinitcpio` ile doğrula.
- GRUB tek kurumsal girdiyi üretmeli. FROZEN parolasız, THAWED ise `cachyadmin`
  doğrulamalı olmalı; parola değil yalnız PBKDF2 özeti root-only dosyada tutulur.
- `btrfs check --repair` yasaktır. EFI/GRUB dosyalarını fiziksel cihazda bilerek
  bozma.
- Güç kesintisi ve boot rollback testlerini önce disposable VM'de yap. Fiziksel
  cihazda ayrıca açık kullanıcı onayı ve tüm yedek/kurtarma koşulları gerekir.
- Her değişiklikte statik testlerin yanında ilgili Btrfs engine, gerçek Btrfs
  loop, GRUB generation ve initramfs build testlerini güvenli hedefte çalıştır.
