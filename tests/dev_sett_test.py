import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_sett_")

from PySide6.QtWidgets import QApplication, QLabel
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
    from gui.model_center import AIModelCenterDialog
    model_center = AIModelCenterDialog(win, win.config)
    model_center.resize(900, 650)
    assert model_center.minimumWidth() <= 900
    print("AIModelCenterDialog 构造成功")
    from gui.reference_center import ReferenceCenterPage
    reference_center = ReferenceCenterPage(win)
    reference_center.resize(900, 650)
    assert reference_center.size().width() == 900
    print("ReferenceCenterPage 构造成功")
    from gui.about_dialog import AboutDialog
    about = AboutDialog(win)
    assert "v" in about.findChildren(QLabel)[1].text()
    print("AboutDialog 构造成功")
except Exception:
    import traceback
    traceback.print_exc()

# 版本: v2.0.1 (2026-08-17) 更新: 模型中心、参考文献中心与 About 构造测试
