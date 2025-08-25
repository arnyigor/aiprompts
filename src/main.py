# main.py
import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from llm_settings import Settings
from main_window import MainWindow
from prompt_manager import PromptManager


def get_base_path() -> Path:
    """Определяет базовый путь для приложения с учетом платформы"""
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            # На macOS путь будет Resources/prompts внутри .app бандла
            # Для приложений в /Applications/MyApp.app/Contents/MacOS/
            return Path(sys.executable).parent
        else:
            # Windows и Linux - папка рядом с exe
            return Path(sys.executable).parent
    else:
        # Запуск из исходников
        return Path(__file__).parent.parent


def setup_logging():
    """Настройка логирования"""
    # Определяем путь для лог-файла
    if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
        # На macOS используем ~/Library/Logs/[AppName]
        log_dir = Path.home() / 'Library' / 'Logs' / 'PromptManager'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'app.log'
    else:
        # На других платформах рядом с приложением
        log_path = Path('app.log')

    # Создаем обработчик для файла с явным указанием кодировки UTF-8
    file_handler = logging.FileHandler(str(log_path), encoding='utf-8')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            file_handler
        ]
    )


# Исправление для Windows - установка Application User Model ID
# Исправление только для Windows
if sys.platform.startswith('win'):
    try:
        import ctypes
        myappid = 'arnyigor.aiprompts.app.version'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except (ImportError, AttributeError, OSError):
        pass  # Игнорируем ошибки даже на Windows

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        base_path = get_base_path()
        prompts_dir = base_path / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        logger.info(f"Платформа: {sys.platform}")
        logger.info(f"Путь к папке с промптами: {prompts_dir}")

        # Инициализируем настройки
        settings = Settings()

        # Настройка политики округления перед созданием QApplication
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Round)

        app = QApplication(sys.argv)

        prompt_manager = PromptManager(storage_path=prompts_dir)
        window = MainWindow(prompt_manager, settings)

        # Текущий скрипт находится в src/
        project_root = Path(__file__).resolve().parent.parent
        icon_path = project_root / "assets" / "icon.png"

        if icon_path.exists():
            icon = QIcon(str(icon_path))  # преобразуем в строку для QIcon
            app.setWindowIcon(icon)
            window.setWindowIcon(icon)  # тоже преобразуем в строку
            logger.info(f"Иконка приложения загружена: {icon_path}")
        else:
            logger.warning(f"Файл иконки не найден: {icon_path}")

        window.show()
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
