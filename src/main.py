# main.py
import sys
import logging
from PyQt6.QtWidgets import QApplication
from prompt_manager import PromptManager
from template_manager import TemplateManager
from main_window import MainWindow


def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )

    # Инициализация компонентов
    app = QApplication(sys.argv)

    # Менеджеры
    prompt_manager = PromptManager()
    template_manager = TemplateManager()

    # Основное окно
    try:
        main_window = MainWindow(prompt_manager)
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error("Ошибка в приложении", exc_info=True)
        raise


if __name__ == "__main__":
    main()