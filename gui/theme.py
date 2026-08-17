APP_QSS = """
QMainWindow, QDialog { background: #F5F6F8; }
QWidget { color: #1D2939; font-family: "Microsoft YaHei UI"; font-size: 13px; }
QToolTip { background: #1D2939; color: white; border: none; padding: 5px 8px; }

QListWidget#sidebar, QListWidget#advNav {
    background: #243447; color: #E6E9EF; border: none; font-size: 13px;
}
QListWidget#sidebar::item, QListWidget#advNav::item {
    min-height: 40px; padding-left: 14px; border: none;
}
QListWidget#sidebar::item:selected, QListWidget#advNav::item:selected {
    background: #356FD3; color: white;
}
QListWidget#sidebar::item:hover, QListWidget#advNav::item:hover { background: #30465F; }

QLabel#appTitle { font-size: 24px; font-weight: 600; color: #1D2939; }
QLabel#pageTitle { font-size: 18px; font-weight: 600; color: #1D2939; padding-bottom: 6px; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; color: #1D2939; }
QLabel#muted { color: #667085; font-size: 12px; }
QLabel#statusSuccess { color: #039855; font-weight: 600; }
QLabel#statusWarning { color: #B54708; font-weight: 600; }
QLabel#statusError { color: #D92D20; font-weight: 600; }

QPushButton {
    min-height: 30px; padding: 4px 14px; background: white;
    border: 1px solid #D0D5DD; border-radius: 4px; color: #1D2939;
}
QPushButton:hover { border-color: #356FD3; color: #285FB8; }
QPushButton:pressed { background: #F2F4F7; }
QPushButton:focus { border: 2px solid #356FD3; }
QPushButton:disabled { color: #98A2B3; background: #F2F4F7; border-color: #E4E7EC; }
QPushButton#primary { background: #356FD3; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #285FB8; color: white; }
QPushButton#danger { color: #D92D20; border-color: #FDA29B; }
QPushButton#danger:hover { background: #FEF3F2; }
QPushButton#modeButton {
    font-size: 15px; font-weight: 600; padding: 18px 22px;
    background: white; border: 1px solid #D0D5DD; border-radius: 6px;
}

QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox, QSpinBox,
QDoubleSpinBox, QListWidget, QTableWidget, QTreeWidget {
    background: white; border: 1px solid #D0D5DD; border-radius: 4px; color: #1D2939;
    selection-background-color: #DCE8FC; selection-color: #1D2939;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { min-height: 30px; padding: 0 8px; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QListWidget:focus, QTableWidget:focus {
    border: 2px solid #356FD3;
}
QComboBox::drop-down { border: none; width: 24px; }

QGroupBox {
    font-weight: 600; color: #1D2939; border: 1px solid #E4E7EC;
    border-radius: 6px; margin-top: 12px; padding-top: 12px; background: white;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QFrame#card { background: white; border: 1px solid #E4E7EC; border-radius: 6px; }
QFrame#toolbar { background: #F2F4F7; border: 1px solid #E4E7EC; border-radius: 6px; }
QFrame#emptyState { background: #F8FAFC; border: 1px dashed #D0D5DD; border-radius: 6px; }

QTableWidget { alternate-background-color: #F8FAFC; gridline-color: #EAECF0; }
QHeaderView::section {
    background: #F2F4F7; color: #1D2939; border: none;
    border-bottom: 1px solid #D0D5DD; padding: 7px; font-weight: 600;
}
QTabWidget::pane { border: 1px solid #D0D5DD; background: white; }
QTabBar::tab { background: #EAECF0; padding: 8px 16px; border: 1px solid #D0D5DD; }
QTabBar::tab:selected { background: white; color: #1D2939; font-weight: 600; }
QCheckBox { spacing: 7px; }

QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #C5CBD3; min-height: 28px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #98A2B3; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

# 版本: v2.0.1 (2026-08-17) 更新: 统一桌面 UI 视觉主题
