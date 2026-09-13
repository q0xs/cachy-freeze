# rc11 laptop test adımları

Bu kontrol `CachyFreeze-Installer-1.0.0rc11.run` içindir. Workstation `1.0.3`
aynı dosyanın içindedir; ayrı Workstation dosyasını kurmanız gerekmez.
Desteklenen CachyOS/KDE, UEFI/GRUB ve Btrfs `@` düzenini kullanın. Laptopta
saklanacak verileri yedekleyin ve kurtarma USB'sini hazır tutun.

## Hazırlık

1. `.run` ve `.run.sha256` dosyalarını laptopta aynı klasöre kopyalayın.
2. Bu klasörde terminal açıp çalıştırın:

   ```bash
   sha256sum --check CachyFreeze-Installer-1.0.0rc11.run.sha256
   chmod 0755 CachyFreeze-Installer-1.0.0rc11.run
   ```

   Sağlama toplamı `OK` olmalıdır.
3. CachyFreeze zaten kuruluysa **THAW COMPUTER → REBOOT NOW** yapın ve
   yeniden açılışta **THAWED** durumunu doğrulayın.
4. Yönetici hesabından yeni installer'ı `sudo` kullanmadan başlatın:

   ```bash
   ./CachyFreeze-Installer-1.0.0rc11.run
   ```

## Uygulamalar ve uyarı

1. Mevcut standart çalışan hesabının adını girip **INSTALL / REPAIR** yapın.
2. Çalışan hesabına giriş yapın. Fotoğraftaki
   `cachy-workstation-idle-agentrc not writable` uyarısı çıkmamalıdır.
3. Chrome, LibreOffice, Slack, AnyDesk, Zoiper ve MicroSIP'i açın. Altısının da
   hem masaüstü hem uygulama menüsü kısayollarını kontrol edin.
4. Slack penceresinin açıldığını ve giriş ekranının kullanılabildiğini doğrulayın.
5. Yöneticiye dönüp yeni installer'da aynı kullanıcı için **CHECK** yapın.
   `OVERALL: PASS`, `Ready for freeze: YES` ve Slack satırında `PASS` olmalıdır.
6. GRUB bakım parolasını girip **INSTALL CACHYFREEZE** yapın. Başarıdan sonra
   **REBOOT NOW** ile yeniden başlatın. Eski sürümden geçişte bu adım kurulu
   uygulamanın Workstation dosyalarını da yeniler.

## FROZEN kontrolü

1. Çalışan hesabına yeniden girişte aynı uyarının çıkmadığını kontrol edin.
2. Yönetici hesabından CachyFreeze'in **FROZEN** gösterdiğini doğrulayın.
3. Çalışan hesabında Slack'i iki kısayoldan da açın.
4. Çalışan masaüstünde `rc11-gecici-test.txt` adlı geçici dosya oluşturun.
   Normal yeniden başlatmadan sonra dosya silinmiş olmalıdır; altı uygulama
   ve kısayolları yerinde kalmalıdır.

## İsteğe bağlı uzun kontrol

Çalışan oturumu açıkken giriş yapmadan bekleyin: 60 dakikada oturum kilitlenmeli,
toplam 120 dakikada laptop kapanmalıdır. Yeniden açıldığında FROZEN durumunu ve
geçici dosyanın silindiğini kontrol edin. Süreleri kısaltmak için gerçek
servisin politikasını değiştirmeyin.

Sonucu paylaşırken uyarının durumu, Slack açılışı, CHECK sonucu ve FROZEN
yeniden başlatma sonrası geçici dosyanın durumunu belirtmeniz yeterli.
