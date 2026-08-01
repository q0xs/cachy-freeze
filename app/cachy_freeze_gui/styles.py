"""Application themes kept separate from widget behavior."""

# ruff: noqa: E501 - QSS rules stay one declaration per line for maintenance.

DARK_STYLE = """
QMainWindow, QWidget { background: #0d1117; color: #e6edf3; font-family: "Inter", "Noto Sans"; }
QWidget#sidebar { background: #111822; border-right: 1px solid #263140; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #ffffff; padding: 8px 4px 18px 4px; }
QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #ffffff; }
QLabel#muted, QLabel#cardCaption { color: #8b9bad; }
QLabel#cardCaption { font-size: 11px; font-weight: 700; }
QLabel#cardValue { font-size: 22px; font-weight: 700; }
QFrame#card { background: #151d27; border: 1px solid #293647; border-radius: 12px; }
QPushButton { background: #1d2938; border: 1px solid #34465d; border-radius: 8px; padding: 9px 13px; color: #edf4ff; font-weight: 600; }
QPushButton:hover { background: #26364a; }
QPushButton:disabled { background: #171d25; color: #667385; border-color: #252d38; }
QPushButton#primary { background: #1668c7; border-color: #2d86e8; }
QPushButton#primary:hover { background: #2379d8; }
QPushButton#danger { background: #7c2530; border-color: #a73b48; }
QPushButton#nav { border: 0; background: transparent; text-align: left; padding: 11px 14px; color: #aebdcd; }
QPushButton#nav:checked { background: #1b2a3d; color: #ffffff; border-left: 3px solid #4c9aff; }
QTableWidget, QPlainTextEdit { background: #111822; alternate-background-color: #141e2a; border: 1px solid #293647; border-radius: 8px; gridline-color: #263140; }
QHeaderView::section { background: #182331; color: #aebdcd; padding: 8px; border: 0; border-bottom: 1px solid #34465d; }
QLineEdit { background: #111822; border: 1px solid #34465d; border-radius: 8px; padding: 9px; }
QProgressBar { background: #202a37; border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #4c9aff; border-radius: 3px; }
QStatusBar { background: #111822; color: #9badc0; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget { background: #f4f7fb; color: #182230; font-family: "Inter", "Noto Sans"; }
QWidget#sidebar { background: #ffffff; border-right: 1px solid #dbe3ec; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #111827; padding: 8px 4px 18px 4px; }
QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #111827; }
QLabel#muted, QLabel#cardCaption { color: #637083; }
QLabel#cardCaption { font-size: 11px; font-weight: 700; }
QLabel#cardValue { font-size: 22px; font-weight: 700; }
QFrame#card { background: #ffffff; border: 1px solid #dbe3ec; border-radius: 12px; }
QPushButton { background: #ffffff; border: 1px solid #cbd6e2; border-radius: 8px; padding: 9px 13px; color: #1f2937; font-weight: 600; }
QPushButton:hover { background: #edf3fa; }
QPushButton:disabled { background: #eef1f5; color: #929dac; }
QPushButton#primary { background: #176dcc; border-color: #176dcc; color: #ffffff; }
QPushButton#danger { background: #b83242; border-color: #b83242; color: #ffffff; }
QPushButton#nav { border: 0; background: transparent; text-align: left; padding: 11px 14px; color: #566477; }
QPushButton#nav:checked { background: #e8f2ff; color: #125cae; border-left: 3px solid #2479d4; }
QTableWidget, QPlainTextEdit { background: #ffffff; alternate-background-color: #f7f9fc; border: 1px solid #dbe3ec; border-radius: 8px; gridline-color: #e2e8f0; }
QHeaderView::section { background: #edf2f7; color: #4f5d70; padding: 8px; border: 0; border-bottom: 1px solid #d3dce7; }
QLineEdit { background: #ffffff; border: 1px solid #cbd6e2; border-radius: 8px; padding: 9px; }
QProgressBar { background: #dce5ef; border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #2479d4; border-radius: 3px; }
QStatusBar { background: #ffffff; color: #566477; }
"""
