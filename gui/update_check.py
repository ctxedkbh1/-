from PySide6.QtCore import QThread, Signal

from core import paths
from core.updater import UpdateCheckError, check_for_update


class UpdateCheckThread(QThread):
    result_ready = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            self.result_ready.emit(check_for_update(paths.VERSION))
        except UpdateCheckError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            self.error.emit(f"检查更新失败：{exc}")


# Version: v2.3.0 (2026-08-19) Update: non-blocking update worker
