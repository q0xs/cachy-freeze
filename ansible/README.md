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
ansible-playbook playbooks/status.yml --syntax-check
ansible-playbook playbooks/thaw.yml --syntax-check
ansible-playbook playbooks/freeze.yml --syntax-check
ansible-playbook playbooks/maintenance.yml --syntax-check
ansible-playbook playbooks/provision.yml --syntax-check
```

Always validate in the lab group before production. Use `--limit lab` for the
first rollout and keep production batch sizes conservative until the target
hardware, KDE display manager, and package mirror behavior are known.
