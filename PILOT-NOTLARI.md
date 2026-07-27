# Pilot Laptop Teknik Notları

Bu paket boot zincirini, initramfs'i ve Btrfs alt birimlerini değiştirir. İlk
kurulum mutlaka yedeği alınmış bir pilot laptopta ve cihazın başında yapılmalı.

İsteğe bağlı olarak ana kurulumdan önce şu salt-okunur ön kontrol çalıştırılır:

```bash
sudo ./deepfreeze/bin/cachy-freeze preflight
```

Komut diski değiştirmez. Aşağıdakileri doğrular:

- UEFI ile açılmış olması
- Kök dosya sisteminin Btrfs olması
- GRUB ve mkinitcpio araçlarının bulunması
- Beklenen `@` kök alt biriminin bulunması
- `/boot` dizininin Btrfs `@` kökü içinde olması
- EFI bölümünün `/boot/efi` konumunda bağlı olması

## Pilot öncesi kayıt

Şu komutların çıktıları saklanmalıdır:

```bash
lsblk -f
findmnt /
findmnt /boot/efi
cat /etc/fstab
cat /etc/mkinitcpio.conf
```

Gerçek kurulumdan önce harici diske sistem yedeği alınmalıdır. Ana ve son
kullanıcı kurulumu için `KURULUM-TR.md` izlenmelidir.
