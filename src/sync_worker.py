# src/sync_worker.py
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from src.sync_manager import SyncManager # <-- Убедитесь, что импорт правильный

class SyncWorker(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    log_message = pyqtSignal(str)  # <-- НОВЫЙ СИГНАЛ

    def __init__(self, sync_manager: SyncManager):
        super().__init__()
        self._sync_manager = sync_manager
        # Пробрасываем оба колбэка
        self._sync_manager._progress_cb = self.progress.emit
        self._sync_manager._log_cb = self.log_message.emit # <-- ПРИВЯЗЫВАЕМ ЛОГИ

    def run(self):
        try:
            self._sync_manager.sync()
            self.finished.emit(True,  "Синхронизация завершена")
        except Exception as e:
            self.finished.emit(False, f"Ошибка: {e}")