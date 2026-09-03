# CachyFreeze Semaphore UI Rehberi

Bu rehber Master PC uzerinde Semaphore UI ile CachyFreeze Ansible
playbook'larini web arayuzunden calistirmak icindir. Semaphore 3000 portundan
acilir, gorev gecmisi PostgreSQL volume'unda kalir.

## 1. Controller'i hazirla

```bash
cd cachy-freeze/ansible
./setup-controller.sh --with-semaphore
```

Betik Ansible, OpenSSH, Docker ve Docker Compose paketlerini kurar. SSH anahtari
yoksa olusturur, `ansible/.semaphore.env` icinde Semaphore icin rastgele DB,
admin ve encryption secret degerleri uretir, sonra PostgreSQL 16 ve Semaphore UI
servislerini baslatir.

Arayuz:

```text
http://localhost:3000
```

Admin kullanicisi varsayilan olarak `admin` olur. Parola
`ansible/.semaphore.env` icindedir ve dosya 0600 izinlidir.

## 2. Proje olustur

1. Semaphore'a girin.
2. **New Project** ile `CachyFreeze Fleet` adinda proje olusturun.
3. Gorevleri ayni proje icinde tutun; bakim, durum ve kurulum loglari boylece
   tek ekranda izlenir.

## 3. Key Store yapilandirmasi

**Project > Key Store** bolumunde iki kayit olusturun.

SSH anahtari:

- Name: `LocalAdm SSH`
- Type: `SSH Key`
- Login: `LocalAdm`
- Private key: Master PC'deki LocalAdm hedeflerine yetkili SSH private key
  icerigi. Genelde `~/.ssh/id_ed25519` kullanilir.

GRUB bakim parolasi:

- Name: `CachyFreeze GRUB Secret`
- Type: `Secret`
- Secret: kurulumda secilen `cachy_freeze_boot_secret` degeri.

Bu degeri inventory veya Git reposuna yazmayin. `provision.yml` sadece ilk
kurulumda bu degere ihtiyac duyar.

## 4. Repository baglantisi

**Project > Repositories > New Repository** bolumunde:

- Name: `cachy-freeze`
- URL: `https://github.com/q0xs/cachy-freeze.git`
- Branch: `main`
- Access key: public repo icin bos birakilabilir; kurumsal fork kullaniliyorsa
  HTTPS token veya SSH key secin.

## 5. Inventory

Mevcut filo icin Semaphore inventory'sine repo ile ayni INI icerigini girin:

```ini
[lab]
lab-01 ansible_host=192.0.2.10 employee_user=WRW21166

[production]
wrw-001 ansible_host=198.51.100.10 employee_user=WRW21166
```

Sifir kurulumda survey ile tek IP sorulacaksa bos bir inventory de
kullanilabilir. `provision.yml`, `target_ip`, `employee_user` ve
`cachy_freeze_target_hosts=semaphore_survey_targets` ekstra degiskenleri
verildiginde hedefi calisma aninda inventory'ye ekler.

## 6. Variable Group

**Project > Variable Groups** altinda `CachyFreeze defaults` olusturun:

```yaml
ansible_user: LocalAdm
ansible_become: true
ansible_become_method: sudo
batch_size: "20%"
```

Kurulum template'i icin ayri bir protected variable group kullanin:

```yaml
cachy_freeze_boot_secret: "{{ vault_cachy_freeze_boot_secret }}"
```

Pratikte bu degeri Semaphore Key Store'daki `CachyFreeze GRUB Secret` kaydindan
template'e baglayin. Parolayi duz metin olarak repository'ye yazmayin.

## 7. Task Template 1: Gece Bakimi

- Name: `Gece Bakimi`
- Type: `Ansible Playbook`
- Repository: `cachy-freeze`
- Playbook: `ansible/playbooks/maintenance.yml`
- Inventory: production veya lab inventory
- Environment / Variable Group: `CachyFreeze defaults`
- Limit: once `lab`, pilot basariliysa `production`

Schedule:

- Cron: `0 3 * * 6,0`
- Timezone: controller'in yerel timezone'u, onerilen `Europe/Warsaw`
- Aciklama: her hafta sonu 03:00'te bakim

Bakim akisi FROZEN makineyi `cachy-freeze thaw --authorized` ile tek seferlik
THAWED acar, paketleri gunceller, Workstation repair/check calistirir, sonra
basarili makineleri tekrar FROZEN moda alir. Hata alan host THAWED birakilir ve
hedefte `/var/log/cachy-freeze-ansible-failure.log` olusturulur.

## 8. Task Template 2: Sifir Kurulum / Provisioning

- Name: `Sifir Kurulum`
- Type: `Ansible Playbook`
- Repository: `cachy-freeze`
- Playbook: `ansible/playbooks/provision.yml`
- Inventory: bos veya lab onboarding inventory
- Variable Group: kurulum icin `cachy_freeze_boot_secret` bagli grup

Survey alanlari:

- `target_ip`: hedef bilgisayarin IP adresi, ornek `192.0.2.10`
- `employee_user`: calisan kullanici adi, ornek `WRW21166`
- `target_name`: istege bagli gorunen host adi, ornek `wrw-001`

Template extra vars:

```yaml
cachy_freeze_target_hosts: semaphore_survey_targets
```

Bu template LocalAdm ile hedefe baglanir, calisan hesabini standart kullanici
olarak hazirlar, Workstation kurulum/check adimlarini gecer, CachyFreeze'i kurar
ve ilk FROZEN boot'u dogrular.

## 9. Task Template 3: Filo Durumu

- Name: `Filo Durumu`
- Type: `Ansible Playbook`
- Repository: `cachy-freeze`
- Playbook: `ansible/playbooks/status.yml`
- Inventory: lab veya production
- Variable Group: `CachyFreeze defaults`

Bu gorev host, IP, FROZEN/THAWED modu, reboot gereksinimi ve employee_user
bilgisini log'a yazar. Semaphore'un son task sonucu dashboard olarak
kullanilabilir.

## 10. Operasyon notlari

- Ilk denemeyi her zaman `lab` limit'i ile calistirin.
- 200-300 PC icin production `batch_size: "20%"` degeriyle baslar. Paket ayna
  hizi ve reboot suresine gore `10%` veya `25%` secilebilir.
- Semaphore portu varsayilan `3000`dur. Degistirmek icin
  `ansible/.semaphore.env` icinde `SEMAPHORE_HTTP_PORT` degerini degistirip
  Compose'u yeniden baslatin.
- `SEMAPHORE_ACCESS_KEY_ENCRYPTION` degerini kaybetmeyin. Bu deger Key Store
  kayitlarini cozmek icin gerekir.
- Backup icin Docker volume'larini ve `ansible/.semaphore.env` dosyasini birlikte
  koruyun.
