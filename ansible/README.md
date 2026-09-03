# CachyFreeze Ansible Fleet Management

This directory contains the monorepo-managed Ansible control plane for
CachyFreeze workstation fleets. It is intended for a dedicated Arch/CachyOS
controller that manages a lab group first, then production in batches.

## Controller Setup

Clone the repository on the Ansible controller and run:

```bash
cd cachy-freeze/ansible
./setup-controller.sh
```

The script installs Ansible, OpenSSH, sshpass, and Python with `pacman`. It
creates an SSH key if the controller does not already have one, then prints the
`ssh-copy-id LocalAdm@HOST` commands needed to trust the controller on target
workstations.

To run the optional web UI on the controller:

```bash
./setup-controller.sh --with-semaphore
```

This also installs Docker and Docker Compose, creates a local
`ansible/.semaphore.env` file with generated secrets, and starts PostgreSQL 16
plus Semaphore UI from `docker-compose.semaphore.yml`. Semaphore listens on
`http://localhost:3000` by default. Change `SEMAPHORE_HTTP_PORT` in
`.semaphore.env` before restarting the Compose stack if the controller already
uses port 3000.

## Inventory

Edit `inventory/hosts.ini`:

```ini
[lab]
lab-01 ansible_host=192.0.2.10 employee_user=WRW21166

[production]
wrw-001 ansible_host=198.51.100.10 employee_user=WRW21166
```

Global defaults live in `inventory/group_vars/all.yml`:

```yaml
ansible_user: LocalAdm
batch_size: "100%"
cachy_freeze_remote_repo: /opt/cachy-freeze
```

The lab group runs at `100%`. Production defaults to `20%`, so a 250-machine
fleet updates in controlled waves instead of all at once. Override with
`-e batch_size=10%` when needed.

Do not store the GRUB maintenance password in plaintext inventory. Provide
`cachy_freeze_boot_secret` through Ansible Vault, `vars_prompt`, or a protected
extra-vars file.

## Zero-Touch Provisioning

Provision fresh targets after CachyOS is installed and `LocalAdm` can connect:

```bash
ansible-playbook playbooks/provision.yml --limit lab --ask-become-pass
```

The playbook:

- installs `/etc/sudoers.d/localadm-ansible` for passwordless `LocalAdm` sudo;
- creates the standard employee account such as `WRW21166`;
- refuses employee membership in `wheel`, `sudo`, `docker`, `lxd`, or equivalent
  admin groups;
- creates employee XDG folders;
- copies the monorepo payload to `/opt/cachy-freeze`;
- runs `workstation-setup EMPLOYEE` and requires `workstation-setup --check`
  to report `OVERALL: PASS` and `Ready for freeze: YES`;
- runs the CachyFreeze installer, reboots, and verifies FROZEN status.

The current CachyFreeze installer creates the initial Golden baseline as part
of installation, so Workstation validation must happen before the install role.

Semaphore surveys can provision one new machine without pre-editing
`hosts.ini`. Pass `target_ip`, `employee_user`, and
`cachy_freeze_target_hosts=semaphore_survey_targets`; `provision.yml` will add
that target to an in-memory inventory group for the run.

## Maintenance

Run routine maintenance with:

```bash
ansible-playbook playbooks/maintenance.yml --limit lab
ansible-playbook playbooks/maintenance.yml --limit production -e batch_size=20%
```

When a host is FROZEN, the role runs:

```bash
cachy-freeze thaw --authorized
```

That sets one `cachy_remote_auth=1` GRUB environment flag and schedules THAWED.
On the next boot, GRUB allows that single THAWED boot without keyboard
authentication. The boot verification service immediately resets
`cachy_remote_auth=0`, so the exception is consumed and cannot silently remain
available for later physical boots.

After THAWED verification, maintenance updates packages with `pacman -Syu
--noconfirm`, repairs Workstation, runs the Workstation health check, freezes
the validated system, reboots, and verifies FROZEN status.

If any update, repair, or health check fails, the rescue path writes
`/var/log/cachy-freeze-ansible-failure.log`, does not run freeze, and leaves the
host THAWED for administrator review.

## Semaphore UI

Semaphore UI is the supported web front end for non-terminal fleet operation.
Use it to run the same playbooks from a browser, watch live logs, and schedule
weekend maintenance.

The included Compose stack:

- runs `postgres:16` with a persistent `semaphore-postgres` volume;
- runs `semaphoreui/semaphore:latest` on port `3000`;
- persists Semaphore config, task data, and temporary working files in Docker
  volumes;
- reads generated admin, database, and access-key-encryption secrets from
  `.semaphore.env`.

Create these templates in Semaphore:

- `maintenance.yml` as **Gece Bakimi**, scheduled with cron `0 3 * * 6,0`;
- `provision.yml` as **Sifir Kurulum**, with survey fields for `target_ip`,
  `target_name`, and `employee_user` such as `WRW21166`;
- `status.yml` as **Filo Durumu** for an on-demand dashboard-style report.

Detailed Turkish operating steps are in
[SEMAPHORE-REHBERI.md](SEMAPHORE-REHBERI.md).

## Status and Emergency Commands

Fleet status:

```bash
ansible-playbook playbooks/status.yml --limit lab
```

Authorized thaw only:

```bash
ansible-playbook playbooks/thaw.yml --limit wrw-001
```

Freeze only after manual validation:

```bash
ansible-playbook playbooks/freeze.yml --limit wrw-001
```

The status role parses `cachy-freeze status` with `from_json` and checks
`result.running_mode` plus `result.reboot_required` before making decisions.

## Validation

Controller-side syntax checks:

```bash
./test-syntax.sh
```

Always validate in the lab group before production. Use `--limit lab` for the
first rollout and keep production batch sizes conservative until the target
hardware, KDE display manager, and package mirror behavior are known.
