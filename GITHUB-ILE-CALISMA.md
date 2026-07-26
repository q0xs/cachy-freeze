# GitHub Üzerinden Linux'ta Çalışma

Bu depo USB taşımadan geliştirme ve yedekleme yapmak için özel GitHub deposu
olarak tutulur.

## Bir defalık hazırlık

CachyOS'ta, tercihen Maintenance modunda:

```bash
sudo pacman -S --needed git github-cli
gh auth login
mkdir -p ~/Projeler
cd ~/Projeler
gh repo clone q0xs/CachyOS-USB-Kurulum
cd CachyOS-USB-Kurulum
```

`gh auth login` sırasında GitHub.com, HTTPS ve tarayıcı ile giriş seçenekleri
kullanılabilir.

## Günlük kısa akış

Çalışmaya başlamadan önce:

```bash
cd ~/Projeler/CachyOS-USB-Kurulum
git switch main
git pull --ff-only
git status
```

Değişikliklerden sonra önce farkı kontrol et:

```bash
git diff
git status
```

Yalnızca amaçlanan dosyaları ekle, kaydet ve GitHub'a gönder:

```bash
git add README.md
git commit -m "README kurulum akisini guncelle"
git push
```

Birden fazla dosya değiştirdiysen `git add README.md` yerine dosyaları açıkça
tek tek yaz. Böylece log, parola veya ilgisiz bir dosyanın yanlışlıkla
gönderilme riski azalır.

## Daha büyük değişiklikler

Kod veya boot akışı değişecekse ayrı dal kullan:

```bash
git switch main
git pull --ff-only
git switch -c calisma/kisa-aciklama
```

Değişiklik ve testlerden sonra:

```bash
git status
git diff
git add dosya1 dosya2
git commit -m "Kisa ve acik degisiklik mesaji"
git push -u origin calisma/kisa-aciklama
```

Ardından GitHub üzerinde bir pull request açıp farkı yeniden incele.

## Frozen sistem uyarısı

- En güvenlisi, depo üzerinde **Maintenance** modunda çalışmaktır.
- Frozen modda çalışırsan commit edilmemiş ve GitHub'a gönderilmemiş yerel
  değişiklikler yeniden başlatmada silinir.
- Yeniden başlatmadan önce `git status` çalıştır ve gerekli commitlerin
  `git push` ile GitHub'a ulaştığını doğrula.
- Depoyu kalıcı ayrı bir bölüme koyduysan bile, o bölümün gerçekten sıfırlama
  kapsamı dışında olduğunu pilot cihazda test et.

## Başka bir Linux cihazında devam etme

```bash
sudo pacman -S --needed git github-cli
gh auth login
gh repo clone q0xs/CachyOS-USB-Kurulum
cd CachyOS-USB-Kurulum
git status
```

GitHub'daki son durum bozulmamışsa USB'den proje kopyalamak gerekmez.

## Sık kullanılan kurtarma komutları

Bir dosyadaki henüz commit edilmemiş değişikliği görmek:

```bash
git diff -- dosya
```

Bir dosyayı son committeki haline döndürmek:

```bash
git restore -- dosya
```

GitHub'daki son commitleri almak:

```bash
git pull --ff-only
```

`git restore` yerel değişikliği siler. Komutu yalnızca farkı kontrol ettikten ve
dosyaya artık ihtiyaç olmadığından emin olduktan sonra kullan.
