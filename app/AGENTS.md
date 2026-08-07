# GUI, helper ve PolicyKit kuralları

Bu dosya `app/` altındaki bütün değişikliklere ek olarak kök `AGENTS.md`
kurallarını uygular.

- GUI ayrıcalıksız kalmalıdır. Root işlemleri yalnız PolicyKit ile korunan,
  tam eylem ve argüman allow-list'i kullanan helper üzerinden yürütülür.
- `QProcess` programını ve argümanlarını ayrı ver; shell komutu oluşturma.
- Çalışan ve GRUB parolalarını yalnız write-channel/stdin ile gönder. Başlatma,
  hata veya iptal durumunda bekleyen gizli veriyi bellek referansından temizle.
- Helper girdilerini regex, argüman sayısı ve sabit değerlerle doğrula. Yol,
  snapshot kimliği, kullanıcı adı veya dosya adında traversal kabul etme.
- Kullanıcı oluşturma ve yönetme akışında CachyOS'un grup veya PolicyKit
  yetkilerini değiştirme; uygulamanın kendi root işlemleri yalnız dar helper
  allow-list'i üzerinden yürüsün.
- QMK/VIA, ayrık GPU, NetworkManager ve pil okuma giriş eylemleri gereksiz
  yönetici penceresi göstermemeli; listede olmayan genel işlem `localadm`
  doğrulaması istemeye devam etmelidir.
- Kurulum finalize düğmesi üç canlı kabul kutusu ve güçlü GRUB parolası olmadan
  çalışmamalıdır. Fiziksel test kanıtını kod kendiliğinden varsayamaz.
- GUI değişikliğinde yedi sayfa smoke testini, backend hata/iptal yolunu, gizli
  veri kanalını ve `.desktop` dosyalarını doğrula.
