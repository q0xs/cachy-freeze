from __future__ import annotations

import unittest

from cachy_freeze_gui.backend import BackendClient
from cachy_freeze_gui.i18n import configure, tr
from cachy_freeze_gui.widgets import retranslate_tree
from cachy_freeze_gui.window import MainWindow
from PyQt6.QtWidgets import QApplication


class InterfaceTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        configure("en")

    def test_turkish_catalog_translates_static_and_dynamic_text(self) -> None:
        configure("tr")
        self.assertEqual(tr("Overview"), "Genel Bakış")
        self.assertEqual(
            tr("Create the standard user 'person_01' and prepare all verified applications?"),
            "Standart kullanıcı oluşturulsun: 'person_01' ve doğrulanmış tüm uygulamalar "
            "hazırlansın mı?",
        )

    def test_window_can_switch_between_turkish_and_english_live(self) -> None:
        configure("tr")
        window = MainWindow(BackendClient())
        try:
            self.assertIn("Genel Bakış", window.nav_buttons[0].text())
            self.assertEqual(window.settings_save_button.text(), "Doğrula ve ayarları kaydet")
            self.assertEqual(window.language_combo.itemText(1), "Türkçe")
            configure("en")
            retranslate_tree(window)
            self.assertIn("Overview", window.nav_buttons[0].text())
            self.assertEqual(window.settings_save_button.text(), "Validate and save settings")
            self.assertEqual(window.language_combo.itemText(1), "Turkish")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
