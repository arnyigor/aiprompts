# main.py
import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from src.prompt_manager import PromptManager
from src.template_manager import TemplateManager
from src.main_window import MainWindow


def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.debug(f"Запуск приложения на платформе: {sys.platform}")

    # Инициализация компонентов
    app = QApplication(sys.argv)
    logger.debug("QApplication инициализировано")

    # Определяем базовый путь для промптов
    if sys.platform == 'darwin':  # macOS
        base_path = Path.home() / "Library" / "Application Support" / "AiPromptManager" / "prompts"
    else:
        base_path = Path("prompts")
    
    logger.debug(f"Базовый путь для промптов: {base_path}")
    base_path.mkdir(parents=True, exist_ok=True)

    # Менеджеры
    try:
        prompt_manager = PromptManager(str(base_path))
        template_manager = TemplateManager()
        logger.debug("Менеджеры инициализированы")
    except Exception as e:
        logger.error("Ошибка инициализации менеджеров", exc_info=True)
        raise

    # Основное окно
    try:
        main_window = MainWindow(prompt_manager)
        main_window.show()
        logger.debug("Главное окно создано и отображено")
        sys.exit(app.exec())
    except Exception as e:
        logger.error("Ошибка в приложении", exc_info=True)
        raise


if __name__ == "__main__":
    main()