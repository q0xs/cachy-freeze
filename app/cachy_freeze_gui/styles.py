"""Focused styling for the installer and two-mode control page."""

# ruff: noqa: E501 - QSS declarations remain one rule per line.

DARK_STYLE = """
QMainWindow, QWidget { background: #313338; color: #f2f3f5; font-family: "Inter", "Noto Sans"; }
QLabel { background: transparent; }
QLabel#pageTitle { font-size: 28px; font-weight: 700; color: #ffffff; }
QLabel#muted, QLabel#cardCaption { color: #b5bac1; }
QLabel#cardCaption { font-size: 12px; font-weight: 700; }
QLabel#modeBadge { background: #5865f2; color: #ffffff; padding: 12px; border-radius: 10px; font-size: 24px; font-weight: 800; }
QFrame#card { background: #2b2d31; border: 0; border-radius: 14px; }
QPushButton { background: #4e5058; border: 0; border-radius: 8px; padding: 12px 16px; color: #f2f3f5; font-weight: 700; }
QPushButton:hover { background: #6d6f78; }
QPushButton:pressed { background: #3f4147; }
QPushButton:disabled { background: #35373c; color: #777c84; }
QPushButton#primary { background: #5865f2; color: #ffffff; }
QPushButton#primary:hover { background: #4752c4; }
QPushButton#danger { background: #da373c; color: #ffffff; }
QLineEdit { background: #1e1f22; border: 1px solid #3f4147; border-radius: 8px; padding: 11px; selection-background-color: #5865f2; }
QLineEdit:focus { border: 1px solid #5865f2; }
QProgressBar { background: #1e1f22; border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #5865f2; border-radius: 3px; }
"""
