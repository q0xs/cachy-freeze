from __future__ import annotations

import unittest
from pathlib import Path


class InstallEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).parents[1]
        cls.builder = (root / "packaging/build-installer.sh").read_text()
        cls.setup = (root / "app/cachy-freeze-setup").read_text()
        cls.gui_main = (root / "app/cachy_freeze_gui/main.py").read_text()
        cls.installer = (root / "installer/install-cachyfreeze.sh").read_text()
        cls.engine_installer = (root / "installer/install-freeze-engine.sh").read_text()

    def test_single_file_builder_embeds_the_required_payload(self) -> None:
        self.assertIn("CachyFreeze-Installer-$version.run", self.builder)
        self.assertIn("src/cachy_freeze", self.builder)
        self.assertIn("installer/install-cachyfreeze.sh", self.builder)
        self.assertIn("SOURCE_DATE_EPOCH", self.builder)
        self.assertIn(".cachyfreeze-payload.sha256", self.builder)
        self.assertIn("/run/cachyfreeze-installer.", self.builder)
        self.assertIn("sha256sum --strict -c", self.builder)

    def test_graphical_bootstrap_uses_policykit_and_installs_pyqt(self) -> None:
        self.assertIn("pkexec", self.setup)
        self.assertIn("pacman -S --needed --noconfirm python python-pyqt6", self.setup)
        self.assertIn("The Python/PyQt6 graphical runtime could not be verified", self.setup)
        self.assertIn("--setup-source", self.setup)
        self.assertIn(".cachyfreeze-root-staged", self.setup)
        self.assertIn("installer staging directory is not root-owned and verified", self.gui_main)

    def test_unprivileged_bootstrap_does_not_traverse_root_only_esp(self) -> None:
        self.assertNotIn("-d /boot/efi/EFI", self.setup)
        self.assertIn("-d /boot/efi/EFI", self.installer)
        self.assertIn("findmnt -n -o TARGET --target /boot/efi", self.setup)
        self.assertIn("findmnt -n -o FSTYPE --target /boot/efi", self.setup)

    def test_installer_prepares_frozen_without_automatic_reboot(self) -> None:
        self.assertIn("cachy-freeze freeze", self.installer)
        self.assertNotIn("systemctl reboot", self.installer)
        self.assertIn("will not reboot automatically", self.installer)

    def test_managed_grub_entry_is_the_direct_hidden_default(self) -> None:
        self.assertIn(
            "set_grub_setting GRUB_DEFAULT cachyos-current", self.engine_installer
        )
        self.assertIn("set_grub_setting GRUB_SAVEDEFAULT false", self.engine_installer)
        self.assertIn("set_grub_setting GRUB_TIMEOUT_STYLE hidden", self.engine_installer)
        self.assertIn("set_grub_setting GRUB_TIMEOUT 1", self.engine_installer)
        self.assertNotIn("GRUB_DEFAULT=saved", self.engine_installer)
        self.assertIn(
            "The managed CachyFreeze GRUB entry is not the direct default.",
            self.engine_installer,
        )


if __name__ == "__main__":
    unittest.main()
