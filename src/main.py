# main.py
import logging
import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow
from src.prompt_manager import PromptManager
from src.llm_settings import Settings


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

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_path))
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # base_path = get_base_path()
        # prompts_dir = base_path / "prompts"
        # prompts_dir.mkdir(exist_ok=True)
        
        logger.info(f"Платформа: {sys.platform}")
        # logger.info(f"Путь к папке с промптами: {prompts_dir}")

        # Инициализируем настройки
        settings = Settings()

        app = QApplication(sys.argv)
        prompt_manager = PromptManager()
        window = MainWindow(prompt_manager, settings)
        window.show()
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
