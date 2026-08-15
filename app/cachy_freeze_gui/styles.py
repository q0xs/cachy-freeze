"""Application themes kept separate from widget behavior."""

# ruff: noqa: E501 - QSS rules stay one declaration per line for maintenance.

DARK_STYLE = """
QMainWindow, QWidget { background: #313338; color: #f2f3f5; font-family: "Inter", "Noto Sans"; }
QLabel { background: transparent; }
QWidget#sidebar { background: #1e1f22; border-right: 0; }
QLabel#brand { font-size: 23px; font-weight: 800; color: #f5fbff; padding: 8px 4px 2px 4px; }
QLabel#sidebarCaption { color: #949ba4; font-size: 10px; font-weight: 800; letter-spacing: 2px; padding: 0 5px 18px 5px; }
QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #ffffff; }
QLabel#muted, QLabel#cardCaption { color: #b5bac1; }
QLabel#cardCaption { font-size: 11px; font-weight: 700; }
QLabel#cardValue { font-size: 22px; font-weight: 700; }
QLabel#modeBadge { background: #5865f2; color: #ffffff; padding: 7px 12px; border-radius: 9px; font-weight: 800; }
QFrame#card { background: #2b2d31; border: 0; border-radius: 14px; }
QGroupBox { background: #2b2d31; border: 0; border-radius: 12px; margin-top: 12px; padding: 16px 12px 12px 12px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #ddecfb; }
QPushButton { background: #4e5058; border: 0; border-radius: 8px; padding: 10px 14px; color: #f2f3f5; font-weight: 650; }
QPushButton:hover { background: #6d6f78; }
QPushButton:pressed { background: #3f4147; }
QPushButton:disabled { background: #35373c; color: #777c84; }
QPushButton#primary { background: #5865f2; color: #ffffff; }
QPushButton#primary:hover { background: #4752c4; }
QPushButton#danger { background: #da373c; color: #ffffff; }
QPushButton#nav { border: 0; background: transparent; text-align: left; padding: 11px 13px; color: #b5bac1; }
QPushButton#nav:hover { background: #35373c; color: #dbdee1; }
QPushButton#nav:checked { background: #404249; color: #ffffff; }
QTableWidget, QPlainTextEdit { background: #2b2d31; alternate-background-color: #303237; border: 0; border-radius: 10px; gridline-color: #3f4147; }
QHeaderView::section { background: #25262a; color: #b5bac1; padding: 9px; border: 0; }
QLineEdit, QComboBox, QSpinBox { background: #1e1f22; border: 1px solid #3f4147; border-radius: 8px; padding: 10px; selection-background-color: #5865f2; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #5865f2; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QProgressBar { background: #1e1f22; border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #5865f2; border-radius: 3px; }
QStatusBar { background: #1e1f22; color: #b5bac1; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget { background: #f4f7fb; color: #182230; font-family: "Inter", "Noto Sans"; }
QLabel { background: transparent; }
QWidget#sidebar { background: #ffffff; border-right: 1px solid #dbe3ec; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #111827; padding: 8px 4px 18px 4px; }
QLabel#sidebarCaption { color: #176dcc; font-size: 10px; font-weight: 800; letter-spacing: 2px; padding: 0 5px 18px 5px; }
QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #111827; }
QLabel#muted, QLabel#cardCaption { color: #637083; }
QLabel#cardCaption { font-size: 11px; font-weight: 700; }
QLabel#cardValue { font-size: 22px; font-weight: 700; }
QLabel#modeBadge { background: #5865f2; color: #ffffff; padding: 7px 12px; border-radius: 9px; font-weight: 800; }
QFrame#card { background: #ffffff; border: 1px solid #dbe3ec; border-radius: 12px; }
QGroupBox { background: #ffffff; border: 1px solid #d8e2ed; border-radius: 12px; margin-top: 12px; padding: 16px 12px 12px 12px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
QPushButton { background: #ffffff; border: 1px solid #cbd6e2; border-radius: 8px; padding: 9px 13px; color: #1f2937; font-weight: 600; }
QPushButton:hover { background: #edf3fa; }
QPushButton:disabled { background: #eef1f5; color: #929dac; }
QPushButton#primary { background: #176dcc; border-color: #176dcc; color: #ffffff; }
QPushButton#danger { background: #b83242; border-color: #b83242; color: #ffffff; }
QPushButton#nav { border: 0; background: transparent; text-align: left; padding: 11px 14px; color: #566477; }
QPushButton#nav:checked { background: #e8f2ff; color: #125cae; border-left: 3px solid #2479d4; }
QTableWidget, QPlainTextEdit { background: #ffffff; alternate-background-color: #f7f9fc; border: 1px solid #dbe3ec; border-radius: 8px; gridline-color: #e2e8f0; }
QHeaderView::section { background: #edf2f7; color: #4f5d70; padding: 8px; border: 0; border-bottom: 1px solid #d3dce7; }
QLineEdit, QComboBox, QSpinBox { background: #ffffff; border: 1px solid #cbd6e2; border-radius: 8px; padding: 9px; }
QProgressBar { background: #dce5ef; border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #2479d4; border-radius: 3px; }
QStatusBar { background: #ffffff; color: #566477; }
"""
