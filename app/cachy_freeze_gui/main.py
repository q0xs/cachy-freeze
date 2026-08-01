"""Desktop application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from .backend import BackendClient
from .window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Cachy Freeze Yönetim Merkezi")
    application.setOrganizationName("CachyOS Workstation")
    application.setFont(QFont("Noto Sans", 10))
    window = MainWindow(BackendClient())
    window.show()
    return application.exec()
