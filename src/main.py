# main.py
import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow
from src.prompt_manager import PromptManager
from src.settings import Settings


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Определяем базовый путь как директорию рядом со скриптом
        base_path = Path(__file__).parent.parent
        prompts_dir = base_path / "prompts"
        prompts_dir.mkdir(exist_ok=True)

        # Инициализируем настройки
        settings = Settings()

        app = QApplication(sys.argv)
        prompt_manager = PromptManager(prompts_dir)
        window = MainWindow(prompt_manager, settings)
        window.show()
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
