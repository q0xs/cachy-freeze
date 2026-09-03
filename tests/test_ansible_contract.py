from __future__ import annotations

import re
import unittest
from pathlib import Path


class AnsibleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).parents[1]
        cls.ansible = cls.root / "ansible"

    def read(self, relative: str) -> str:
        return (self.ansible / relative).read_text(encoding="utf-8")

    def test_required_ansible_tree_exists(self) -> None:
        for relative in (
            "setup-controller.sh",
            "ansible.cfg",
            "inventory/hosts.ini",
            "inventory/group_vars/all.yml",
            "inventory/group_vars/lab.yml",
            "inventory/group_vars/production.yml",
            "playbooks/provision.yml",
            "playbooks/maintenance.yml",
            "playbooks/status.yml",
            "playbooks/thaw.yml",
            "playbooks/freeze.yml",
            "roles/localadm_bootstrap/tasks/main.yml",
            "roles/localadm_bootstrap/templates/sudoers.j2",
            "roles/cachy_workstation/tasks/main.yml",
            "roles/cachy_workstation/tasks/ensure_employee.yml",
            "roles/cachy_workstation/tasks/install_apps.yml",
            "roles/cachy_workstation/tasks/repair_apps.yml",
            "roles/cachy_workstation/tasks/health_check.yml",
            "roles/cachy_freeze/tasks/get_status.yml",
            "roles/cachy_freeze/tasks/thaw.yml",
            "roles/cachy_freeze/tasks/freeze.yml",
            "roles/cachy_freeze/tasks/install.yml",
            "roles/cachy_freeze/tasks/verify.yml",
            "README.md",
        ):
            self.assertTrue((self.ansible / relative).is_file(), relative)

    def test_ansible_cfg_is_fleet_tuned(self) -> None:
        config = self.read("ansible.cfg")
        self.assertIn("forks = 50", config)
        self.assertIn("pipelining = True", config)
        self.assertIn("inventory = inventory/hosts.ini", config)

    def test_playbooks_use_serial_batching_and_json_contract(self) -> None:
        for playbook in ("provision.yml", "maintenance.yml", "thaw.yml", "freeze.yml"):
            self.assertIn(
                "serial: \"{{ batch_size | default('100%') }}\"",
                self.read(f"playbooks/{playbook}"),
            )
        status_role = self.read("roles/cachy_freeze/tasks/get_status.yml")
        self.assertIn("from_json", status_role)
        self.assertIn("cachy_freeze_status.running_mode", status_role)
        self.assertIn("cachy_freeze_status.reboot_required is boolean", status_role)

    def test_ansible_tasks_use_fqcn_modules(self) -> None:
        bare_modules = re.compile(
            r"^\s*-?\s*(assert|command|copy|debug|fail|file|getent|include_role|"
            r"include_tasks|reboot|set_fact|stat|template|user):",
            re.MULTILINE,
        )
        for path in self.ansible.rglob("*.yml"):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(bare_modules.search(text), path)

    def test_maintenance_fails_without_freezing(self) -> None:
        maintenance = self.read("playbooks/maintenance.yml")
        self.assertIn("block:", maintenance)
        self.assertIn("rescue:", maintenance)
        self.assertIn("Host was intentionally left THAWED", maintenance)
        self.assertIn("was not frozen", maintenance)

    def test_controller_bootstrap_is_self_documenting(self) -> None:
        script = self.read("setup-controller.sh")
        self.assertIn("pacman -Syu --needed --noconfirm ansible openssh sshpass python", script)
        self.assertIn("ssh-keygen -t ed25519", script)
        self.assertIn("ssh-copy-id LocalAdm@", script)

    def test_documentation_mentions_fleet_workflows(self) -> None:
        ansible_readme = self.read("README.md")
        project_readme = (self.root / "README.md").read_text(encoding="utf-8")
        turkish_install = (self.root / "KURULUM-TR.md").read_text(encoding="utf-8")
        self.assertIn("Remote Fleet Management with Ansible", project_readme)
        self.assertIn("Ansible ile Uzaktan Toplu Yonetim", turkish_install)
        self.assertIn("maintenance.yml", ansible_readme)
        self.assertIn("cachy-freeze thaw --authorized", ansible_readme)


if __name__ == "__main__":
    unittest.main()
