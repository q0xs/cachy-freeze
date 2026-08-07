# CachyFreeze Boot Recovery

Bu belge belirli bir laptopun disk UUID'sini icermez. Temiz kurulumdan sonra
UUID'ler degisecegi icin eski UUID kullanmak tehlikelidir.

1. GRUB MENUSU GELIYORSA
------------------------

GRUB parolanla su girisi sec:

  THAWED

2. SIYAH EKRAN VAR AMA TTY ACILIYORSA
--------------------------------------

Ctrl+Alt+F3 tuslarina bas. Yonetici hesabinla giris yap:

  sudo /usr/local/sbin/cachy-freeze thaw
  sudo reboot

3. GRUB GELMIYORSA
------------------

CachyOS Live USB'yi UEFI modunda ac. Once diskleri sadece listele:

  lsblk -f

Btrfs kok bolumunun UUID'sini ve EFI bolumunu not et. Eski bir belgeden UUID
kopyalama. Emin degilsen mount, chroot veya onarim komutu calistirma; teknik
destek al ve bu USB klasorunu goster.

4. ONEMLI
----------

- @, @golden veya @active Btrfs alt birimlerini silme.
- Diski yeniden formatlama.
- btrfs check --repair calistirma.
- THAWED girisiyle acmayi dene.
- Btrfs snapshot tek basina disk yedegi degildir.
