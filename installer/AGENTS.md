# Provisioning kuralları

Bu dosya `installer/` altındaki bütün değişikliklere ek olarak kök `AGENTS.md`
kurallarını uygular.

- Bu betikler normal kullanıcının terminalden çalıştıracağı giriş noktaları
  değildir. Desteklenen akış grafik uygulama → PolicyKit helper → doğrulanmış
  installer zinciridir.
- `CACHY_SETUP_NONINTERACTIVE=1` yolunda kullanıcı ve GRUB parolalarını yalnız
  stdin'den oku; argümana, ortama, loga veya geçici dosyaya koyma ve kullanımdan
  sonra değişkeni unset et.
- Paket, mkinitcpio veya GRUB değişmeden önce preflight ve bakım `@` kökü
  zorunludur. Boot yapılandırmasının geri alınabilir yedeğini koru.
- AUR derlemesini root olarak yapma. Kaynak URL, checksum, ZIP/path traversal ve
  beklenen executable kontrollerini zayıflatma.
- Kullanılan mutlak hedefleri doğrula. Geniş veya hesaplanmış bir dizine
  doğrulamadan recursive silme/taşıma uygulama.
- Çalışan hesabını her oluşturma/geri yükleme yolunda `wheel` ve `sudo`
  gruplarından çıkar; `localadm` hesabının etkin parolasını ve wheel üyeliğini
  doğrula.
- Paket/boot yazımı sırasında yeniden başlatma veya güç kesme önerme. GUI'nin
  işlem tamamlandıktan sonraki reboot akışını kullan.
- Değişiklikte Bash syntax, ShellCheck, statik test, GUI provisioning testi ve
  mümkünse disposable CachyOS VM entegrasyonunu çalıştır.
