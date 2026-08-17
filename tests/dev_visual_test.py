import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_visual_data_")

from PySide6.QtWidgets import QApplication

from main import apply_light_theme


def assert_nonblank(image, label):
    colors = set()
    step_x = max(1, image.width() // 100)
    step_y = max(1, image.height() // 60)
    for x in range(0, image.width(), step_x):
        for y in range(0, image.height(), step_y):
            colors.add(image.pixelColor(x, y).rgba())
    assert len(colors) >= 6, f"{label} screenshot appears blank: {len(colors)} colors"


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    apply_light_theme(app)
    from gui.main_window import MainWindow
    from gui.model_center import AIModelCenterDialog

    output_dir = tempfile.mkdtemp(prefix="pa_visual_shots_")
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    window.sidebar.setCurrentRow(window.stack.count() - 1)
    app.processEvents()
    reference_image = window.grab().toImage()
    reference_path = os.path.join(output_dir, "reference-center.png")
    reference_image.save(reference_path)
    assert_nonblank(reference_image, "reference center")

    dialog = AIModelCenterDialog(window, window.config)
    dialog.resize(1100, 760)
    dialog.show()
    app.processEvents()
    model_image = dialog.grab().toImage()
    model_path = os.path.join(output_dir, "model-center.png")
    model_image.save(model_path)
    assert_nonblank(model_image, "model center")
    dialog.close()
    window.close()
    print(f"VISUAL TEST OK\n{model_path}\n{reference_path}")


if __name__ == "__main__":
    main()

# 版本: v2.0.1 (2026-08-17) 更新: 模型与参考中心渲染截图测试
