import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_sett_")

from PySide6.QtWidgets import QApplication
from main import apply_light_theme

app = QApplication([])
app.setStyle("Fusion")
apply_light_theme(app)

from gui.main_window import MainWindow
win = MainWindow()

try:
    from gui.main_window import SettingsDialog
    dlg = SettingsDialog(win, win.config)
    print("SettingsDialog 构造成功")
    from gui.model_manager import ModelManagerDialog
    dlg2 = ModelManagerDialog(win, win.config)
    print("ModelManagerDialog 构造成功")
except Exception:
    import traceback
    traceback.print_exc()

# 版本: v1.5.1 (2026-08-16) 更新: 修复设置对话框无响应
