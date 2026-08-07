# CachyFreeze Development Workflow

Bu depo USB taşımadan geliştirme ve yedekleme yapmak için özel GitHub deposu
olarak tutulur.

Bu belge teknisyen/Codex geliştirme akışıdır; normal çalışan kurulumu için
terminal talimatı değildir. Normal kurulum yalnız grafik uygulamadan yapılır.

## Codex CLI zorunlu akışı

1. Önce `AGENTS.md` ve `CODEX-CLI-DEVAM-TALIMATI.md` dosyalarını oku.
2. `git status --short`, `git remote -v`, `git log -3 --oneline` çalıştır.
   Kullanıcı değişikliklerini silme, stash etme veya ezme.
3. Uzak değişiklik varsa yalnız temiz ve uyumlu durumda `git pull --ff-only`
   kullan. Merge commit veya zorla push oluşturma.
4. Kod değişmeden önce mevcut test kapısını çalıştır; hata varsa önce kök nedeni
   belirle. Yapılmamış testi geçmiş gösterme.
5. Parola, token, cihaz UUID'si, gerçek kullanıcı verisi, audit/log çıktısı veya
   parola hash'ini stage etme. Gizli değerleri komut argümanına koyma.
6. Yalnız ilgili dosyaları adlarıyla `git add -- dosya1 dosya2` biçiminde ekle;
   staged diff ve `git diff --cached --check` sonucunu incele.
7. Bu projedeki güncel kullanıcı tercihi PR açmadan, kısa ve anlaşılır
   commitlerle doğrudan `main` dalına push etmektir. Kullanıcı farklı bir akış
   isterse en son açık talimatı uygula.
8. GitHub Actions tamamlanana kadar izle. Başarısızsa ilgili job logunu incele,
   düzelt, test et, yeni commit gönder ve tamamen yeşil sonucu doğrula.

Minimum kod kapısı:

```bash
ruff check src app/cachy_freeze_gui tests
ruff format --check src app/cachy_freeze_gui tests
python -m unittest discover -s tests -v
SHELLCHECK_OPTS=--severity=error bash deepfreeze/tests/static.sh
QT_QPA_PLATFORM=offscreen bash deepfreeze/tests/ui-smoke.sh
```

Boot/Btrfs entegrasyon testlerini yalnız disposable VM veya açıkça ayrılmış
pilot cihazda çalıştır. Fiziksel cihazda mutasyon, reboot veya yıkıcı test için
`CODEX-CLI-DEVAM-TALIMATI.md` güvenlik kapılarını uygula.

## Bir defalık hazırlık

CachyOS'ta, tercihen Maintenance modunda:

```bash
sudo pacman -S --needed git github-cli
gh auth login
mkdir -p ~/Projeler
cd ~/Projeler
gh repo clone q0xs/cachy-freeze
cd cachy-freeze
```

`gh auth login` sırasında GitHub.com, HTTPS ve tarayıcı ile giriş seçenekleri
kullanılabilir.

## Günlük kısa akış

Çalışmaya başlamadan önce:

```bash
cd ~/Projeler/cachy-freeze
git switch main
git pull --ff-only
git status
```

Değişikliklerden sonra önce farkı kontrol et:

```bash
git diff
git status
git diff --check
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

Push sonrasında GitHub CLI varsa koşuyu izle:

```bash
gh run list --limit 5
gh run watch --exit-status
```

`gh` yoksa GitHub Actions sayfasını veya GitHub API'sindeki commit koşusunu
kontrol et. Yalnız push komutunun başarılı olması kalite kapısının geçtiği
anlamına gelmez.

## İsteğe bağlı dal/PR akışı

İnsan geliştirici veya kullanıcı ayrıca PR isterse ayrı dal kullan:

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

Ardından GitHub üzerinde bir pull request açıp farkı yeniden incele. Bu bölüm,
Codex için yukarıda tanımlanan güncel doğrudan-`main` tercihini kendiliğinden
değiştirmez.

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
gh repo clone q0xs/cachy-freeze
cd cachy-freeze
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
