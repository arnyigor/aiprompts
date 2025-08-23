# src/sync_worker.py
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from sync_manager import SyncManager

class SyncWorker(QObject):
    finished = pyqtSignal(bool, str)   # успех?, итог
    progress = pyqtSignal(str)         # короткий статус

    def __init__(self, sync_manager: SyncManager):
        super().__init__()
        # пробрасываем progress-сигнал прямо из SyncManager
        self._sync_manager = sync_manager
        self._sync_manager._progress_cb = self.progress.emit

    def run(self):
        try:
            self._sync_manager.sync()
            self.finished.emit(True,  "Синхронизация завершена")
        except Exception as e:
            self.finished.emit(False, f"Ошибка: {e}")
